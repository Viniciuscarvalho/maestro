# Maestro — Arquitetura do Sistema

> Documentação técnica do sistema integrado de Skills com RAG.

---

## O Problema: Por que Skills direto não escala

### Sem Maestro: Claude carrega tudo no contexto

```
~/.claude/skills/
├── swift-concurrency/
│   ├── SKILL.md                  ← Claude lê  (4KB)
│   └── references/
│       ├── async-await-basics.md ← Claude lê  (8KB)
│       ├── actors.md             ← Claude lê  (6KB)
│       ├── sendable.md           ← Claude lê  (7KB)
│       ├── threading.md          ← Claude lê  (5KB)
│       ├── tasks.md              ← Claude lê  (6KB)
│       ├── migration.md          ← Claude lê  (5KB)
│       ├── core-data.md          ← Claude lê  (4KB)
│       ├── performance.md        ← Claude lê  (5KB)
│       ├── testing.md            ← Claude lê  (4KB)
│       ├── memory-management.md  ← Claude lê  (3KB)
│       ├── async-sequences.md    ← Claude lê  (4KB)
│       └── linting.md            ← Claude lê  (3KB)
├── swift-testing/                ← + 8 reference files
├── swift-testing-expert/         ← + 10 reference files
├── swiftui-expert/               ← + 11 reference files
├── swift-best-practices/         ← + 4 reference files
└── swift-code-reviewer/          ← + 8 reference files
```

| Cenário          | Arquivos   | Tamanho   | Tokens         |
|------------------|-----------|-----------|----------------|
| 6 skills         | ~52        | ~250 KB   | ~65.000        |
| 20 skills        | ~200       | ~1 MB     | ~250.000       |
| 100 skills       | ~1000      | ~5 MB     | **IMPOSSÍVEL** |

**Resultado:** Claude ou ignora as skills, ou fica lento, ou excede o contexto.

---

### Com Maestro: Claude carrega UM skill leve

```
.claude/skills/
└── maestro/
    └── SKILL.md    ← SÓ ISSO no contexto (~3KB = ~750 tokens)

~/.maestro/skills/  ← NÃO no contexto, só no RAG
├── swift-concurrency/
├── swift-testing/
├── swiftui-expert/
└── ... (100+ skills)
```

**Resultado:** 750 tokens fixos, independente de quantas skills existem.

---

## Arquitetura de 3 Camadas

```
┌─────────────────────────────────────────────────────────┐
│                     CAMADA 1: GATEWAY                   │
│                                                         │
│         .claude/skills/maestro/SKILL.md                 │
│                                                         │
│  - É o ÚNICO skill que Claude vê no contexto            │
│  - Contém: instruções de como usar MCP tool             │
│  - Contém: SKILL INDEX (resumo de 1 linha por skill)    │
│  - ~750 tokens fixos, não cresce com mais skills        │
│                                                         │
│  Claude lê isso e sabe:                                 │
│  "Para qualquer task, chame search_skills primeiro"     │
└────────────────────────┬────────────────────────────────┘
                         │ chama MCP tool
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   CAMADA 2: RAG ENGINE                  │
│                                                         │
│         maestro-mcp (processo MCP via stdio)            │
│                                                         │
│  - Auto-indexa ~/.maestro/skills/ na primeira chamada   │
│  - 5 técnicas de qualidade:                             │
│      T1: concept expansion                              │
│      T2: skill fingerprinting                           │
│      T3: contextual embeddings                          │
│      T4: hybrid search + RRF                            │
│      T5: cross-encoder reranking                        │
│  - Retorna 5-7 chunks relevantes (~2000 tokens)         │
│  - Cache semântico para queries repetidas               │
└────────────────────────┬────────────────────────────────┘
                         │ busca vetorial + BM25
                         ▼
┌─────────────────────────────────────────────────────────┐
│                CAMADA 3: KNOWLEDGE BASE                 │
│                                                         │
│  ~/.maestro/skills/    (todas as skills, fora contexto) │
│  ~/.maestro/vectordb/  (ChromaDB com embeddings)        │
│  ~/.maestro/cache/     (cache de queries)               │
│  ~/.maestro/graph/     (grafo de conceitos)             │
│                                                         │
│  100 skills × 50 chunks = 5000 chunks indexados         │
│  Mas cada query busca em ~150 chunks (fingerprinting)   │
│  E retorna top 5-7 (reranking)                          │
└─────────────────────────────────────────────────────────┘
```

---

## Fluxo Completo (Passo a Passo)

### Primeira vez (setup)

```bash
# 1. Instalar
pip install maestro-rag

# 2. Setup automático: move skills, instala gateway, configura MCP, indexa
maestro-setup
```

O script cria `~/.maestro/skills/`, move as skills, instala o gateway em `.claude/skills/maestro/SKILL.md` e configura `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "maestro": { "command": "maestro-mcp" }
  }
}
```

### Cada task (uso normal)

```
Usuário: "Fix Sendable warning in NetworkService"
         │
         ▼
Claude lê Gateway SKILL.md (750 tokens)
         │  "Devo chamar search_skills antes de responder"
         ▼
Claude chama MCP:
  search_skills("Sendable warning actor NetworkService")
         │
         ▼
RAG Engine processa:
  ├── T1 Concept expansion:  +isolation, +data race, +crossing boundary
  ├── T2 Fingerprinting:     swift-concurrency (0.91), swift-best-practices (0.67)
  ├── T3 Hybrid search:      semântica + BM25 em 120 chunks
  ├── T4 RRF fusion:         combina rankings
  └── T5 Reranker:           top 20 → top 5
         │
         ▼
Retorna 5 chunks (~2000 tokens):
  1. sendable.md § Reference Types (0.912)
  2. actors.md § Isolation Boundaries (0.889)
  3. sendable.md § Region-Based Isolation (0.834)
  4. migration.md § Swift 6 Sendable (0.798)
  5. threading.md § Nonisolated Functions (0.756)
         │
         ▼
Claude aplica o conhecimento e corrige o código
```

### Tokens usados

| | SEM Maestro (6 skills) | COM Maestro (100 skills) |
|-|------------------------|--------------------------|
| Context carregado | 65.000 tokens | 750 + 2.000 tokens |
| Útil p/ task | ~3.000 tokens (5%) | ~2.000 tokens (~74%) |
| Desperdício | 95% | ~0% |

---

## Modo Claude.ai (sem MCP)

Claude.ai não suporta MCP, então o fluxo é diferente:

1. Gateway `SKILL.md` está no projeto (Claude.ai vê)
2. Gateway contém o **SKILL INDEX** (resumo de cada skill)
3. Claude sabe QUAIS skills existem, mas não tem o conteúdo completo
4. Gateway instrui Claude a pedir contexto ao usuário:

```
Claude: "Para ajudar com Sendable, preciso do contexto específico.
        Execute: maestro context 'Sendable warning actor'
        e cole o resultado aqui."
```

5. Usuário roda no terminal, cola o resultado
6. Claude trabalha com ~2000 tokens de conhecimento preciso

### Alternativa: Skill Index inline

Para Claude.ai, o Gateway pode incluir um índice compacto:

```
100 skills × 1 linha (50 tokens) = 5.000 tokens no Gateway
```

Isso permite que Claude SAIBA o que cada skill cobre, mesmo sem o conteúdo completo.
Claude pode então pedir contexto específico quando necessário.

---

## Auto-Indexação

O RAG indexa automaticamente, sem passo manual:

```python
# Na primeira chamada search_skills:
if not self._collection or self._collection.count() == 0:
    self.index()  # auto-indexa ~/.maestro/skills/

# Em chamadas subsequentes:
if self._needs_reindex():              # detecta mudanças via hash
    self._incremental_index()          # só re-indexa arquivos alterados
```

Triggers de re-indexação:
- Primeira chamada (índice vazio)
- Arquivo `.md` modificado (hash diferente)
- Novo diretório em `~/.maestro/skills/`
- Comando explícito: `maestro index`

---

## Comparação de Abordagens

| Aspecto               | Skills direto        | RAG v1 (MiniLM)        | Maestro (v2)            |
|-----------------------|----------------------|------------------------|-------------------------|
| Setup                 | Zero                 | Manual index           | Auto-setup + auto-index |
| Tokens (6 skills)     | ~65K                 | ~2K                    | ~2.7K                   |
| Tokens (100 skills)   | Impossível           | ~2K mas impreciso      | ~2.7K e preciso         |
| Precisão              | 100% (tudo carregado)| ~60% (embedding fraco) | ~90% (5 técnicas)       |
| Latência              | 0ms                  | ~100ms                 | ~300ms                  |
| Funciona sem MCP      | ✓                    | ✗                      | ✓ (modo degradado)      |
| Escala                | Até ~10 skills       | Até ~50 skills         | 100+ skills             |

---

## Estrutura de Diretórios Final

```
Projeto do usuário/
├── .claude/
│   ├── skills/
│   │   └── maestro/
│   │       └── SKILL.md    ← Gateway (SÓ ISSO no contexto)
│   └── mcp.json            ← Config MCP

~/.maestro/
├── skills/                 ← Todas as skills reais
│   ├── swift-concurrency/
│   │   ├── SKILL.md
│   │   └── references/*.md
│   ├── swift-testing/
│   ├── swiftui-expert/
│   └── ... (100+ skills)
├── vectordb/               ← ChromaDB embeddings
├── cache/                  ← Cache semântico
├── graph/                  ← Grafo de conceitos
├── index_meta.yaml         ← Hashes para change detection
└── config.yaml             ← Configuração
```
