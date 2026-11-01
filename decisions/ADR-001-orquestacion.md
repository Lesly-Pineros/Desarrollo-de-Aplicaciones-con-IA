# ADR-001 — Motor de orquestación del runtime: Python plano (v0.1) → LangGraph (v0.2)

- **Estado:** Aceptado
- **Fecha:** 2026-10-31
- **Contexto:** El runtime de InvestiQ necesita un workflow con router + varios nodos agénticos (Explicador, Educador, ML-Consultor, Comparador) y tools deterministas. Se evaluó usar LangGraph/LangChain desde v0.1.

## Decisión

Implementar la orquestación de **v0.1 en Python plano** (función `router` + tools como funciones puras + estado en `dict`/Pydantic), **sin LangGraph ni LangChain**. Para el acceso al LLM se usa únicamente el cliente `langchain-nvidia-ai-endpoints` (ChatNVIDIA), no el resto de abstracciones de LangChain. **LangGraph se introduce en v0.2** cuando el flujo lo justifique.

## Justificación

- **Complejidad proporcional:** un grafo de ~4 nodos no requiere un framework de estado. El valor de LangGraph (bucles, estado compartido complejo, checkpointing, paralelismo real) aún no aplica en el piloto.
- **Depuración y tests más simples:** funciones puras se testean y trazan sin capas intermedias.
- **Menos dependencias** y menor superficie de fallo para v0.1.
- **Migración barata:** al mantener las **tools como funciones puras** y un **contrato de nodos estable**, pasar a LangGraph en v0.2 es un cambio acotado.

## Disparadores para migrar a LangGraph (v0.2)

- Aparecen bucles o reintentos con estado entre nodos.
- Estado compartido complejo entre pasos / necesidad de checkpointing.
- Paralelismo real entre nodos.
- El workflow multiagente crece más allá de lo que un router simple mantiene legible.

## Consecuencias

- (+) v0.1 más simple, rápida de construir y depurar; fiel a "complejidad proporcional".
- (+) Contrato de tools/nodos reutilizable en la migración.
- (−) Trabajo de migración en v0.2 (mitigado por el diseño con funciones puras).
- El requisito "workflow multiagente documentado" se cumple en ambas versiones; el **framework** se difiere, no el diseño multiagente.

## Alternativas descartadas

- **LangGraph desde v0.1:** framework por adelantado sin beneficio claro en el piloto.
- **LangChain completo:** peso adicional sin beneficio; se usa solo el cliente ChatNVIDIA.
