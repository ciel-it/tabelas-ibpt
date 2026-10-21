# scripts/sincronizar.py — roda na Action; sem dependencias fora da stdlib
"""Le o espelho publico, baixa ZIPs de versoes que ainda nao temos, valida e atualiza versoes.json.
Nao faz commit: a Action abre um PR e uma pessoa confere contra o e-mail do IBPT."""
import csv, hashlib, io, json, re, sys, urllib.request, zipfile
from datetime import datetime
from pathlib import Path

ESPELHO = 'https://api.github.com/repos/luizinhoh2o1/tabelas-ibpt/contents/repositorio-ibpt'
RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / 'repositorio-ibpt'
INDICE = RAIZ / 'versoes.json'
CABECALHO = ['codigo', 'ex', 'tipo', 'descricao', 'nacionalfederal', 'importadosfederal', 'estadual',
             'municipal', 'vigenciainicio', 'vigenciafim', 'chave', 'versao', 'fonte']
RE_ZIP = re.compile(r'TabelaIBPTax_(\d+\.\d+\.[A-Z])\.zip$')
RE_CSV = re.compile(r'TabelaIBPTax([A-Z]{2})(\d+\.\d+\.[A-Z])\.csv$', re.I)


def baixar(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'ciel-it/tabelas-ibpt'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def validar(conteudo, versao):
    z = zipfile.ZipFile(io.BytesIO(conteudo))
    csvs = [n for n in z.namelist() if RE_CSV.search(n)]
    assert len(csvs) == 27, f'{versao}: esperado 27 CSVs, veio {len(csvs)}'
    ufs, inicio, fim = set(), None, None
    for nome in csvs:
        uf, v = RE_CSV.search(nome).groups()
        assert v.upper() == versao, f'{nome}: versao no nome difere de {versao}'
        rd = csv.DictReader(io.StringIO(z.read(nome).decode('cp1252'), newline=''), delimiter=';')
        assert [c.strip().lower() for c in rd.fieldnames] == CABECALHO, f'{nome}: cabecalho'
        n = 0
        for row in rd:
            if not row['codigo']:
                continue
            n += 1
            assert row['versao'].strip().upper() == versao, f'{nome}: coluna versao'
            for col in ('nacionalfederal', 'importadosfederal', 'estadual', 'municipal'):
                assert 0 <= float(row[col].replace(',', '.')) <= 100, f'{nome}: {col} fora de 0-100'
            i, f = (datetime.strptime(row[k].strip(), '%d/%m/%Y').date() for k in ('vigenciainicio', 'vigenciafim'))
            inicio, fim = inicio or i, fim or f
            assert (i, f) == (inicio, fim), f'{nome}: vigencia inconsistente'
        assert n > 1000, f'{nome}: so {n} linhas'
        ufs.add(uf.upper())
    assert len(ufs) == 27, f'{versao}: UFs {sorted(ufs)}'
    assert inicio < fim, f'{versao}: vigencia invertida'
    return inicio, fim


def main():
    indice = json.loads(INDICE.read_text(encoding='utf-8')) if INDICE.exists() else []
    temos = {i['versao'] for i in indice}
    ultimo_fim = max((i['vigencia_fim'] for i in indice), default='0000-00-00')
    remoto = json.loads(baixar(ESPELHO).decode())
    novos = []
    # o espelho guarda o historico desde 2015: so interessa o que e mais novo que o indice
    # (indice vazio: apenas a mais nova do espelho)
    def chave(v):
        a, s, l = v.split('.')
        return (int(a), int(s), l)
    candidatas = sorted(((chave(m.group(1)), m.group(1), item) for item in remoto
                         if (m := RE_ZIP.search(item['name'])) and m.group(1) not in temos), key=lambda t: t[0])
    if temos:
        maior = max(chave(v) for v in temos)
        candidatas = [c for c in candidatas if c[0] > maior]
    else:
        candidatas = candidatas[-1:]
    for _, versao, item in candidatas:
        conteudo = baixar(item['download_url'])
        inicio, fim = validar(conteudo, versao)
        assert fim.isoformat() > ultimo_fim, f'{versao}: vigencia {fim} nao e posterior a {ultimo_fim}'
        destino = PASTA / f'TabelaIBPTax_{versao}.zip'
        destino.write_bytes(conteudo)
        novos.append({'versao': versao, 'vigencia_inicio': inicio.isoformat(), 'vigencia_fim': fim.isoformat(),
                      'arquivo': f'repositorio-ibpt/{destino.name}', 'sha256': hashlib.sha256(conteudo).hexdigest(), 'ufs': 27})
        print('nova versao', versao, inicio, fim)
    if not novos:
        print('nada novo'); return 0
    indice = sorted(indice + novos, key=lambda i: i['vigencia_inicio'])
    INDICE.write_text(json.dumps(indice, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
