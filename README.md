# tabelas-ibpt

Repositório público com as tabelas do IBPT (Lei 12.741/2012, "De Olho no Imposto") consumidas pela
localização Odoo da CIEL (`l10n_br_ciel_it_account`). Cada versão é um ZIP com 27 CSVs (um por UF) em
`repositorio-ibpt/`, listado no índice `versoes.json`.

## Formato do índice

`versoes.json` é uma lista JSON, da versão mais antiga para a mais nova. A última é a vigente.

```json
[
  {
    "versao": "26.2.B",
    "vigencia_inicio": "2026-09-20",
    "vigencia_fim": "2026-10-31",
    "arquivo": "repositorio-ibpt/TabelaIBPTax_26.2.B.zip",
    "sha256": "0d5c5cd35b8cc5581847c79c530ea8d4ad5a0f7dd9a4a0ec3542afda0a99fc65",
    "ufs": 27
  }
]
```

## Como o Odoo consome

O módulo lê `<base>/versoes.json`, pega o **último item**, baixa `<base>/<arquivo>` e confere o SHA-256
antes de gravar qualquer coisa (hash divergente = nada é gravado). A `<base>` vem do parâmetro de sistema
`l10n_br_ciel_it_account.ibpt_repositorio_url`; o padrão é
`https://raw.githubusercontent.com/ciel-it/tabelas-ibpt/main`.

## Sincronização semanal (GitHub Action)

`.github/workflows/sincronizar.yml` roda toda segunda-feira (09:00 UTC) e sob demanda
(`workflow_dispatch`). `scripts/sincronizar.py` (só stdlib) consulta o espelho
`luizinhoh2o1/tabelas-ibpt`, ignora versões que já temos ou mais antigas que o índice, baixa as novas e
valida: 27 CSVs, cabeçalho, versão no nome e na coluna, alíquotas entre 0 e 100, vigência consistente e
posterior à última do índice. Se houver versão nova, a Action abre um PR (branch `ibpt/nova-versao`).
A Action **não** faz merge sozinha.

### Checklist do merge (humano)

0. Pré-requisito do repositório: em Settings › Actions › General › Workflow permissions, habilitar "Allow GitHub Actions to create and approve pull requests"; sem isso a Action não consegue abrir o PR.

1. Conferir **versão** e **vigência** do PR contra o e-mail do IBPT e o portal De Olho no Imposto.
2. Conferir que o item novo é o último de `versoes.json` e que o ZIP está em `repositorio-ibpt/`.
3. Só então fazer o merge. A partir dele, o "Atualizar agora" do Odoo passa a enxergar a versão.

## Subir uma versão à mão

1. Copiar o ZIP recebido por e-mail do IBPT para `repositorio-ibpt/TabelaIBPTax_<versao>.zip`.
2. Calcular o SHA-256:

   ```
   py -c "import hashlib;print(hashlib.sha256(open('repositorio-ibpt/TabelaIBPTax_X.zip','rb').read()).hexdigest())"
   ```
3. Acrescentar o item ao final de `versoes.json` (mesmo formato acima, `ufs` = 27, vigência conforme o e-mail).
4. Commit e PR, com o mesmo checklist de conferência.

## Aviso sobre a origem

O espelho `luizinhoh2o1/tabelas-ibpt` é uma fonte **de terceiros**. O SHA-256 do índice protege a
**integridade** do arquivo entre este repositório e o Odoo, mas não prova a **autenticidade** da tabela:
por isso a conferência humana contra o IBPT antes do merge é obrigatória.
