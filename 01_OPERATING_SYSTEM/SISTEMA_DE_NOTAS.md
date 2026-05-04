---
title: Sistema de Notas
tags:
  - operating-system
  - notas
  - sistema
aliases:
  - Sistema de Notas
---

# Sistema de Notas

Como notas são criadas, categorizadas e evoluem no vault.

---

## Estrutura Padrão de uma Nota

```markdown
---
title: [Título]
tags:
  - [categoria]
aliases:
  - [Nome alternativo]
---

# Título

## Objetivo
## Contexto
## Dados / Evidências
## Interpretação
## Premissas
## Riscos
## Pendências
## Próximos Passos
## Links Relacionados
## Data da última atualização
```

---

## Tipos de Nota

| Tipo | Local | Propósito |
|---|---|---|
| **Meta** | `00_META/` | Governança do vault |
| **Operacional** | `01_OPERATING_SYSTEM/` | Protocolos e rituais |
| **Empresa** | `03_COMPANIES/[TICKER]/` | Cobertura de empresa |
| **Setor** | `04_SECTORS/` | Inteligência setorial |
| **Fonte** | `05_DATA_SOURCES/` | Manual de fonte |
| **Modelo** | `06_MODELS/` | Documentação de modelo financeiro |
| **Valuation** | `07_VALUATION/` | Metodologia de valuation |
| **Pesquisa** | `08_RESEARCH/` | Nota investigativa |
| **Skill** | `09_SKILLS/` | Capacidade documentada |
| **Workflow** | `10_WORKFLOWS/` | Fluxo operacional |
| **Prompt** | `11_PROMPTS/` | Instrução para agente |
| **Validação** | `13_VALIDATION/` | Checklist e regra de alerta |
| **Output** | `14_OUTPUTS/` | Entregável produzido |
| **Template** | `15_TEMPLATES/` | Modelo reutilizável |
| **Decisão** | `18_DECISIONS/` | Registro de decisão |
| **Erro** | `19_ERROR_LIBRARY/` | Erro documentado |
| **Aprendizado** | `20_LEARNING_LOG/` | Insight registrado |

---

## Ciclo de Vida de uma Nota

```
1. Rascunho      → criada, incompleta, sem revisão
2. Em revisão    → conteúdo completo, aguardando validação
3. Validada      → revisada, pronta para uso
4. Publicada     → integrada ao sistema, linkada
5. Arquivada     → obsoleta, movida para 25_ARCHIVE/
```

Use a propriedade `status` no frontmatter:

```yaml
status: rascunho | em-revisao | validado | publicado | arquivado
```

---

## Linking

- Use `[[Wikilinks]]` para conexões **internas** ao vault
- Use `[texto](url)` apenas para **links externos**
- Prefira links específicos: `[[Empresa#Seção]]` em vez de apenas `[[Empresa]]`
- Crie links mesmo para notas que ainda não existem — eles orientam o que precisa ser criado

---

## Embeds

Use `![[Nota#Seção]]` para embutir seções de outras notas quando fizer sentido (ex: embutir checklist de outra nota dentro de um workflow).

---

## Propriedades Essenciais

```yaml
---
title:       # nome legível da nota
tags:        # lista de tags
aliases:     # nomes alternativos
status:      # rascunho / validado / arquivado
empresa:     # ticker (se aplicável)
setor:       # setor (se aplicável)
versao:      # ex: v1, v2
data:        # data de criação
---
```

---
*Última atualização: 2026-04-16*
