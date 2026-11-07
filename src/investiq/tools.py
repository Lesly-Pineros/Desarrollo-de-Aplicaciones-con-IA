from datetime import datetime, timezone
import hashlib
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from investiq.data.models import InstrumentFeature, MLClusterRun, UserPreference
from investiq.domain import FilingItem, NewsItem, PreferenceInput, SourceReference
from investiq.education import EDUCATION_CATALOGUE, DefinitionView
from investiq.instruments import INSTRUMENT_BY_SYMBOL
from investiq.ml.similarity import load_model_artifact, similar_instruments as find_similar
from investiq.ml.volatility import assign_volatility_buckets
from investiq.providers.market_data import market_quote
from investiq.providers.news import news
from investiq.providers.sec import sec_docs
from investiq.settings import Settings

# Public text view retained for callers such as the opt-in live verifier.
GLOSSARY = DefinitionView()


def normalize_symbol(value: str | None) -> str | None:
    if not value:
        return None
    symbol = value.strip().upper()
    return symbol if symbol in INSTRUMENT_BY_SYMBOL else None


def market_quote_tool(session: Session, symbol: str, settings: Settings):
    return market_quote(session, symbol, settings)


def news_tool(session: Session, symbol: str, settings: Settings):
    return news(session, symbol, settings)


def sec_docs_tool(session: Session, symbol: str, settings: Settings):
    return sec_docs(session, symbol, settings)


def education_tool(topic: str, *, followup: str = "") -> str | None:
    from investiq.language import canonical_education_topic

    term = canonical_education_topic(topic)
    if not term:
        return None
    if any(word in followup.casefold() for word in ("ejemplo", "sencill", "no entend", "más fácil", "mas facil")):
        return EDUCATION_CATALOGUE[term].example
    return GLOSSARY[term]


def instr_features(session: Session, symbol: str) -> dict | None:
    symbol = symbol.strip().upper()
    feature = session.get(InstrumentFeature, symbol)
    if not feature:
        return None
    return {
        "symbol": symbol,
        "volatility": feature.volatility,
        "mean_peer_correlation": feature.mean_peer_correlation,
        "beta": feature.beta,
        "sector": feature.sector,
        "volatility_bucket": feature.volatility_bucket,
        "calculated_at": feature.calculated_at.isoformat(),
    }


def feature_sources(session: Session, symbols: list[str]) -> list[SourceReference]:
    """Trace metrics to actual local feature records even without a clustering run."""
    sources = []
    for symbol in dict.fromkeys(symbols):
        feature = session.get(InstrumentFeature, symbol)
        if feature:
            sources.append(SourceReference(
                source_id=f"features:{symbol}:{feature.calculated_at.isoformat()}",
                title=f"Características históricas de {symbol} ({feature.calculated_at.isoformat()})",
                url=f"local://features/{symbol}", provider="Datos históricos locales",
                published_at=feature.calculated_at,
            ))
    return sources


def volatility_bucket(session: Session, target: str) -> list[dict]:
    if target not in {"baja", "media", "alta"}:
        return []
    features = session.exec(select(InstrumentFeature)).all()
    if not features:
        return []
    buckets = assign_volatility_buckets({feature.symbol: feature.volatility for feature in features})
    return [
        {**instr_features(session, feature.symbol), "volatility_bucket": buckets[feature.symbol]}
        for feature in sorted(features, key=lambda item: (item.volatility, item.symbol))
        if buckets.get(feature.symbol) == target
    ]


def _latest_artifact(session: Session) -> dict:
    run = session.exec(
        select(MLClusterRun)
        .where(MLClusterRun.passed_thresholds.is_(True))
        .order_by(MLClusterRun.created_at.desc())
    ).first()
    if not run:
        raise RuntimeError("No hay una ejecución de clustering aprobada; ejecuta `investiq-data train`.")
    artifact_dir = Path("ml/artifacts").resolve()
    artifact_path = Path(run.artifact_path)
    if not artifact_path.is_absolute():
        artifact_path = (Path.cwd() / artifact_path).resolve()
    if artifact_dir not in artifact_path.parents:
        raise RuntimeError("La ruta del artefacto ML está fuera de ml/artifacts.")
    if not artifact_path.is_file():
        raise RuntimeError("No se encontró el artefacto ML registrado.")
    return load_model_artifact(artifact_path)


def local_model_source(session: Session) -> SourceReference | None:
    run = session.exec(
        select(MLClusterRun)
        .where(MLClusterRun.passed_thresholds.is_(True))
        .order_by(MLClusterRun.created_at.desc())
    ).first()
    if not run:
        return None
    return SourceReference(
        source_id=f"ml:{run.run_id}",
        title=f"Features y clustering InvestiQ ({run.observation_start} a {run.observation_end})",
        url=f"local://ml/artifacts/{Path(run.artifact_path).name}",
        provider="Pipeline ML local",
        published_at=run.created_at,
    )


def similar_instruments(session: Session, reference: str, *, top_n: int = 5) -> list[dict]:
    reference = reference.strip().upper()
    if reference not in INSTRUMENT_BY_SYMBOL:
        raise KeyError("Símbolo fuera del universo cubierto.")
    artifact = _latest_artifact(session)
    rows = session.exec(select(InstrumentFeature).order_by(InstrumentFeature.symbol)).all()
    by_symbol = {item.symbol: item for item in rows}
    columns = artifact["columns"]
    numeric_rows = []
    for symbol in artifact["symbols"]:
        feature = by_symbol.get(symbol)
        if not feature:
            continue
        row = {
            "volatility": feature.volatility,
            "mean_peer_correlation": feature.mean_peer_correlation,
            "beta": feature.beta,
        }
        for column in columns:
            if column.startswith("sector_"):
                row[column] = float(feature.sector == column.removeprefix("sector_"))
        numeric_rows.append((symbol, row))
    features = pd.DataFrame({symbol: row for symbol, row in numeric_rows}).T.reindex(columns=columns)
    found = find_similar(reference, features, artifact, top_n=top_n)
    return [
        {
            **(instr_features(session, symbol) or {}),
            "cluster_label": cluster,
            "distance": distance,
        }
        for symbol, cluster, distance in found
    ]


def exploration_candidates(session: Session, decision) -> tuple[list[dict], MLClusterRun]:
    from investiq.ml.exploration import rank_candidates

    artifact = _latest_artifact(session)
    run = session.exec(select(MLClusterRun).where(MLClusterRun.passed_thresholds.is_(True))
                       .order_by(MLClusterRun.created_at.desc())).first()
    if (run is None or artifact.get("observation_start") != run.observation_start.isoformat()
            or artifact.get("observation_end") != run.observation_end.isoformat()):
        raise ValueError("El período del modelo y el registro local no coinciden.")
    rows = session.exec(select(InstrumentFeature)).all()
    numeric = {}
    for feature in rows:
        if feature.symbol not in artifact["symbols"]:
            continue
        if feature.calculated_at.replace(tzinfo=timezone.utc) > run.created_at.replace(tzinfo=timezone.utc):
            raise ValueError("Las características cambiaron después de entrenar; vuelve a entrenar.")
        row = {"volatility": feature.volatility, "beta": feature.beta,
               "mean_peer_correlation": feature.mean_peer_correlation}
        row.update({column: float(feature.sector == column.removeprefix("sector_"))
                    for column in artifact["columns"] if column.startswith("sector_")})
        numeric[feature.symbol] = row
    frame = pd.DataFrame(numeric).T.reindex(columns=artifact["columns"]).sort_index()
    fingerprint = artifact.get("feature_fingerprint")
    if fingerprint:
        actual = hashlib.sha256(frame.round(12).to_csv(float_format="%.12g").encode("utf-8")).hexdigest()
        if actual != fingerprint:
            raise ValueError("Las características no coinciden con la huella del entrenamiento.")
    if artifact.get("run_id", run.run_id) != run.run_id or run.universe_size != len(frame):
        raise ValueError("La ejecución no coincide con el artefacto o universo local.")
    return rank_candidates(frame, artifact, decision), run


def _preference_for_user(session: Session, email: str) -> PreferenceInput | None:
    saved = session.get(UserPreference, email)
    if not saved:
        return None
    return PreferenceInput(
        volatility_target=saved.volatility_target,
        sector=saved.sector,
        reference_symbol=saved.reference_symbol,
        beta_target=saved.beta_target,
    )


def compare_instruments(session: Session, email: str, symbols: list[str], *, use_preferences: bool = True) -> list[dict]:
    preferences = _preference_for_user(session, email) if use_preferences else None
    preferences = preferences or PreferenceInput()
    unique = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if normalize_symbol(symbol)))
    if not 2 <= len(unique) <= 4:
        raise ValueError("Indica entre 2 y 4 símbolos cubiertos para comparar.")

    weights = {
        "volatility": 0.40,
        "sector": 0.30,
        "similarity": 0.15,
        "beta": 0.15,
    }
    results = []
    reference_cluster = {}
    if preferences.reference_symbol:
        try:
            artifact = _latest_artifact(session)
            reference_cluster = artifact["labels"]
        except RuntimeError:
            reference_cluster = {}
    for symbol in unique:
        feature = instr_features(session, symbol)
        if not feature:
            continue
        components: dict[str, float] = {}
        if preferences.volatility_target:
            components["volatility"] = float(feature["volatility_bucket"] == preferences.volatility_target)
        if preferences.sector:
            components["sector"] = float(feature["sector"].casefold() == preferences.sector.casefold())
        if preferences.reference_symbol:
            components["similarity"] = float(
                reference_cluster.get(symbol) is not None
                and reference_cluster.get(symbol) == reference_cluster.get(preferences.reference_symbol)
            )
        if preferences.beta_target is not None:
            components["beta"] = max(0.0, 1.0 - abs(feature["beta"] - preferences.beta_target) / 2.0)
        weight_sum = sum(weights[key] for key in components)
        score = sum(weights[key] * value for key, value in components.items()) / weight_sum if weight_sum else None
        results.append({**feature, "score": round(score * 100, 2) if score is not None else None, "components": components})
    return sorted(results, key=lambda row: (-(row["score"] or 0), row["symbol"]))


def source_references(quote, news_items: list[NewsItem], filings: list[FilingItem]) -> list[SourceReference]:
    references: list[SourceReference] = []
    if quote and quote.source:
        references.append(quote.source)
    references.extend(
        SourceReference(
            source_id=item.source_id,
            title=item.title,
            url=item.url,
            provider=item.provider,
            published_at=item.published_at,
            delayed=item.delayed,
        )
        for item in news_items
    )
    references.extend(
        SourceReference(
            source_id=item.source_id,
            title=f"SEC {item.form} presentado {item.filing_date}",
            url=item.url,
            provider="SEC",
        )
        for item in filings
    )
    return references
