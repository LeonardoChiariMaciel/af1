"""
relatorio.py

MÓDULO DE RELATÓRIO HTML.

Papel no fluxo: última etapa. Reúne os resultados da execução (indicadores,
referência setorial e interpretação) em UM arquivo .html autocontido:
CSS dentro do próprio arquivo e gráficos como imagens em base64. Por isso
o relatório abre em qualquer navegador, mesmo sem internet.

Entradas : empresa, indicadores, média setorial, interpretação, falhas dos
           concorrentes e a pasta de saída.
Saídas   : montar_secoes() devolve os blocos de HTML (usados também pela
           interface web); gerar_relatorio() grava o arquivo em relatorios/.

Gráficos: matplotlib com backend "Agg" (desenha em memória, sem abrir janela).
"""

import base64
import html
import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # backend sem janela: precisa vir antes do pyplot
import matplotlib.pyplot as plt

from indicadores import (DIAS_NO_ANO, INDICADORES_EM_DIAS,
                         INDICADORES_PERCENTUAIS, formatar_indicador)
from interpretacao import (FAMILIAS, NOMES_INDICADORES, TOLERANCIA_RELATIVA)
from referencia_setorial import MIN_PARES
from setores import SETOR_DESTAQUE

DISCIPLINA = "Administração Financeira (CAD 167), UFMG, Sistemas de Informação"
FONTE_DOS_DADOS = "Yahoo Finance, acessado por meio da biblioteca yfinance."

# Cores dos gráficos, alinhadas à identidade visual da interface (preto e amarelo).
# Sobre fundo branco, o amarelo puro tem pouco contraste; por isso a média dos
# pares usa um âmbar mais escuro, além de linha tracejada e marcador quadrado
# (a diferença não depende só da cor).
COR_EMPRESA = "#0b0b0c"
COR_PARES = "#c98500"
COR_TEXTO = "#0b0b0c"
COR_TEXTO_SECUNDARIO = "#5c5c60"
COR_GRADE = "#e6e6e3"

# Folha de estilo ÚNICA do projeto: a mesma usada pela interface web
# (static/css/style.css). Ao gerar o relatório, ela é copiada para dentro do
# HTML, para que o arquivo continue autocontido (sem depender de arquivos
# externos nem de internet).
ARQUIVO_CSS = Path(__file__).resolve().parent / "static" / "css" / "style.css"


def _ler_css():
    """Lê o CSS do projeto para embutir no relatório."""
    return ARQUIVO_CSS.read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------------

def _esc(texto):
    """Escapa texto para HTML (evita que caracteres como & ou < quebrem a página)."""
    return html.escape(str(texto))


def texto_indicador(nome, valor):
    """
    Texto de uma célula: usa formatar_indicador (indicadores.py) e deixa a
    primeira letra maiúscula, de modo que None aparece como "Não disponível".
    """
    texto = formatar_indicador(nome, valor)
    return texto[0].upper() + texto[1:]


def _ano_de_referencia(indicadores, media_setorial):
    """Ano mais recente em que a empresa e a média setorial têm dados. None se não houver."""
    comuns = set(indicadores) & set(media_setorial)
    return max(comuns) if comuns else None


# ----------------------------------------------------------------------
# Tabela
# ----------------------------------------------------------------------

def _celula_referencia(nome, ano_ref, media_setorial):
    """Célula da coluna da média dos pares: valor e n, sem esconder o tamanho da amostra."""
    info = media_setorial.get(ano_ref, {}).get(nome) if ano_ref else None
    if info is None or info["media"] is None:
        return '<td class="indisponivel">Não disponível</td>'
    texto = f"{_esc(texto_indicador(nome, info['media']))} (n = {info['n']})"
    if info["n"] < MIN_PARES:
        texto += " <small>referência limitada</small>"
    return f'<td class="destaque">{texto}</td>'


def _tabela_indicadores(indicadores, media_setorial):
    """Tabela: linhas = indicadores, colunas = anos (em ordem) + média dos pares."""
    anos = sorted(indicadores)
    ano_ref = _ano_de_referencia(indicadores, media_setorial)

    cabecalho = "<th>Indicador</th>" + "".join(f"<th>{ano}</th>" for ano in anos)
    if ano_ref:
        cabecalho += f"<th>Média dos pares em {ano_ref}</th>"

    linhas = []
    for familia, nomes in FAMILIAS.items():
        colunas = len(anos) + (2 if ano_ref else 1)
        linhas.append(f'<tr class="linha-familia"><th colspan="{colunas}">{_esc(familia)}</th></tr>')
        for nome in nomes:
            celulas = [f"<td>{_esc(NOMES_INDICADORES[nome])}</td>"]
            for ano in anos:
                valor = indicadores[ano][nome]
                classe = ' class="indisponivel"' if valor is None else ""
                celulas.append(f"<td{classe}>{_esc(texto_indicador(nome, valor))}</td>")
            if ano_ref:
                celulas.append(_celula_referencia(nome, ano_ref, media_setorial))
            linhas.append("<tr>" + "".join(celulas) + "</tr>")

    return (f'<div class="tabela-rolagem"><table><thead><tr>{cabecalho}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


# ----------------------------------------------------------------------
# Gráficos
# ----------------------------------------------------------------------

def _unidade(nome):
    """Rótulo do eixo vertical e fator de escala do indicador."""
    if nome in INDICADORES_PERCENTUAIS:
        return "% (percentual)", 100.0
    if nome in INDICADORES_EM_DIAS:
        return "dias", 1.0
    return "vezes (razão)", 1.0


def _serie(nome, anos, fonte, escala):
    """
    Valores do indicador para cada ano, na ordem de 'anos'.

    None vira NaN, e o matplotlib deixa uma LACUNA na linha. Ausência de
    dado nunca é desenhada como zero. 'fonte' é uma função (ano -> valor).
    """
    valores = []
    for ano in anos:
        valor = fonte(ano)
        valores.append(float("nan") if valor is None else valor * escala)
    return valores


def _grafico_familia(familia, nomes, indicadores, media_setorial):
    """
    Desenha UM gráfico (imagem PNG em base64) para a família.

    Cada indicador ganha um painel próprio, porque as unidades diferem
    (ex.: razão e vezes) e não se deve usar dois eixos no mesmo painel.
    Em cada painel: linha cheia = empresa; linha tracejada = média dos
    pares, somente nos anos com n >= MIN_PARES.
    """
    anos = sorted(indicadores)
    colunas = 2 if len(nomes) > 1 else 1
    linhas = (len(nomes) + colunas - 1) // colunas
    figura, eixos = plt.subplots(linhas, colunas, figsize=(4.8 * colunas, 3.1 * linhas),
                                 squeeze=False)

    for posicao, nome in enumerate(nomes):
        eixo = eixos[posicao // colunas][posicao % colunas]
        rotulo_y, escala = _unidade(nome)

        empresa = _serie(nome, anos, lambda a: indicadores[a][nome], escala)

        def media_valida(ano):
            info = media_setorial.get(ano, {}).get(nome)
            return info["media"] if info and info["n"] >= MIN_PARES else None
        pares = _serie(nome, anos, media_valida, escala)

        tem_empresa = any(v == v for v in empresa)   # v == v é falso só para NaN
        tem_pares = any(v == v for v in pares)
        eixo.plot(anos, empresa, color=COR_EMPRESA, marker="o", linewidth=2, markersize=6,
                  label="Empresa")
        if tem_pares:
            eixo.plot(anos, pares, color=COR_PARES, marker="s", linestyle="--", linewidth=2,
                      markersize=6, label="Média dos pares")

        if not tem_empresa:
            # Sem dado da empresa: o aviso fica no topo e diz de quem é a lacuna
            eixo.text(0.5, 0.95, "Empresa: indicador não disponível", transform=eixo.transAxes,
                      ha="center", va="top", fontsize=8, color=COR_TEXTO_SECUNDARIO,
                      bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9})
        if tem_empresa or tem_pares:
            eixo.legend(loc="best", fontsize=8, frameon=False)

        eixo.set_title(NOMES_INDICADORES[nome], fontsize=10, color=COR_TEXTO)
        eixo.set_xlabel("Ano", fontsize=8, color=COR_TEXTO_SECUNDARIO)
        eixo.set_ylabel(rotulo_y, fontsize=8, color=COR_TEXTO_SECUNDARIO)
        eixo.set_xticks(anos)
        eixo.tick_params(labelsize=8, colors=COR_TEXTO_SECUNDARIO)
        eixo.grid(True, color=COR_GRADE, linewidth=0.8)
        eixo.set_axisbelow(True)
        for lado in ("top", "right"):
            eixo.spines[lado].set_visible(False)

    # Esconde painéis sobrando (família com número ímpar de indicadores)
    for posicao in range(len(nomes), linhas * colunas):
        eixos[posicao // colunas][posicao % colunas].axis("off")

    figura.suptitle(f"{familia}: evolução ao longo dos anos", fontsize=12, color=COR_TEXTO)
    figura.tight_layout()

    memoria = io.BytesIO()
    figura.savefig(memoria, format="png", dpi=110)
    plt.close(figura)   # libera a memória da figura
    return base64.b64encode(memoria.getvalue()).decode("ascii")


def _secao_graficos(indicadores, media_setorial):
    """HTML dos quatro gráficos (um por família), com a imagem embutida."""
    partes = []
    for familia, nomes in FAMILIAS.items():
        imagem = _grafico_familia(familia, nomes, indicadores, media_setorial)
        partes.append(
            f'<figure class="grafico" data-familia="{_esc(familia)}">'
            f'<img alt="Gráfico de evolução: {_esc(familia)}" '
            f'src="data:image/png;base64,{imagem}">'
            f'<figcaption>Linha cheia: empresa. Linha tracejada: média dos pares, exibida '
            f'apenas nos anos com pelo menos {MIN_PARES} pares com dado. Lacunas indicam '
            f'indicador não disponível (nunca zero).</figcaption></figure>')
    return "".join(partes)


# ----------------------------------------------------------------------
# Interpretação e notas
# ----------------------------------------------------------------------

def _secao_interpretacao(interpretacao):
    """HTML dos textos de cada família."""
    partes = []
    for familia, conteudo in interpretacao["familias"].items():
        itens = "".join(f"<li>{_esc(i)}</li>" for i in conteudo["itens"])
        notas = "".join(f'<div class="nota">{_esc(n)}</div>' for n in conteudo["notas"])
        partes.append(f'<section class="familia"><h3>{_esc(familia)}</h3>{notas}<ul>{itens}</ul></section>')
    return "".join(partes)


def _indicadores_indisponiveis(indicadores):
    """Nomes (legíveis) dos indicadores que são None em pelo menos um ano."""
    return [NOMES_INDICADORES[nome] for familia in FAMILIAS.values() for nome in familia
            if any(indicadores[ano][nome] is None for ano in indicadores)]


def _notas_metodologicas(empresa, indicadores, media_setorial, falhas, pares_utilizados):
    """
    Lista de notas metodológicas e limitações.

    Só entram notas que se aplicam à execução: as simplificações de
    cálculo valem sempre; as demais dependem dos dados obtidos.
    """
    anos = sorted(indicadores)
    notas = [
        f"Convenção de {DIAS_NO_ANO} dias no ano para os prazos médios. É uma premissa "
        f"metodológica do trabalho (alguns autores usam 360 dias).",
        "ROA, ROE e prazos médios usam o saldo de fim de ano, e não a média entre o início "
        "e o fim do período.",
        "O prazo médio de pagamento (PMP) usa o CMV como base, em vez das compras do "
        "período, que não constam das demonstrações.",
        "Endividamento e dívida sobre patrimônio usam o passivo total (todas as obrigações, "
        "sem o patrimônio líquido), e não a dívida financeira.",
        "O patrimônio líquido considerado é o dos controladores; a participação de "
        "não controladores fica fora de passivo e patrimônio.",
        f"Fonte dos dados: {FONTE_DOS_DADOS} Os valores seguem a classificação contábil "
        f"da fonte, que pode diferir das demonstrações originais da empresa e ter "
        f"quebras entre anos. Anos disponíveis para esta empresa: "
        f"{', '.join(str(a) for a in anos)}.",
        f"A tolerância de {TOLERANCIA_RELATIVA:.0%} usada para classificar variações como "
        f"\"relativamente estáveis\" e valores como \"em linha com a média\" é uma decisão "
        f"metodológica desta aplicação, e não uma regra de livro nem uma regra universal "
        f"de finanças.",
        "As expressões \"geralmente favorável\" seguem uma leitura simplificada e dependem "
        "do modelo de negócio. Não há faixas absolutas de bom ou ruim e o relatório não "
        "constitui recomendação de investimento.",
    ]

    # Referência setorial: quem entrou, quem falhou e por quê
    if pares_utilizados:
        nomes = ", ".join(f"{p['nome']} ({p['ticker']})" for p in pares_utilizados)
        notas.append(
            f"Referência setorial: média aritmética simples de {len(pares_utilizados)} "
            f"empresa(s) comparável(is): {nomes}. A lista de comparáveis é fixa e a amostra é "
            f"pequena; a média é sensível a valores extremos e não representa o setor inteiro. "
            f"Cada média informa o n de empresas com dado válido.")
    else:
        notas.append("Nenhuma empresa comparável foi capturada; não há referência setorial "
                     "e a análise se limita à evolução da própria empresa.")
    for ticker, motivo in falhas:
        notas.append(f"Concorrente não utilizado: {ticker}. Motivo: {motivo}")

    indisponiveis = _indicadores_indisponiveis(indicadores)
    if indisponiveis:
        notas.append("Indicadores não disponíveis em ao menos um ano, por falta da conta "
                     f"necessária na fonte: {', '.join(indisponiveis)}.")
    if empresa["setor"] == SETOR_DESTAQUE:
        notas.append("Em locadoras de veículos a frota fica no imobilizado, e não em estoque "
                     "de mercadorias. PME, ciclos operacional e financeiro e liquidez seca "
                     "têm leitura limitada ou ficam indisponíveis.")
    if empresa["ticker"] == "RENT3.SA" and len(anos) >= 2:
        notas.append("Comparabilidade histórica: a combinação de negócios entre Localiza e "
                     "Unidas foi concluída em 1º de julho de 2022 (data informada pelas "
                     "companhias e noticiada pela imprensa financeira). Os resultados de "
                     "2022 tendem a refletir a operação combinada apenas em parte do ano. "
                     "Variações relevantes entre anos podem refletir mudanças de estrutura "
                     "empresarial, aquisições ou combinações de negócios, e não apenas "
                     "crescimento orgânico.")
    return notas


# ----------------------------------------------------------------------
# Comparação setorial
# ----------------------------------------------------------------------

def _secao_comparacao(indicadores, media_setorial, falhas, pares_utilizados):
    """
    Bloco "Comparação com empresas do setor": quem entrou na referência,
    quantos pares são, quem falhou e avisos de amostra pequena.
    """
    partes = []
    if not pares_utilizados:
        partes.append('<p class="aviso">Nenhuma empresa comparável foi capturada; não há '
                      'referência setorial e a análise se limita à evolução da própria '
                      'empresa.</p>')
    else:
        itens = "".join(f"<li>{_esc(p['nome'])} ({_esc(p['ticker'])})</li>"
                        for p in pares_utilizados)
        partes.append(f"<p>Quantidade de pares: <strong>{len(pares_utilizados)}</strong></p>"
                      f"<p>Empresas utilizadas:</p><ul>{itens}</ul>")
        if len(pares_utilizados) < MIN_PARES:
            partes.append('<p class="aviso">A quantidade de empresas comparáveis é pequena. '
                          'A média apresentada deve ser interpretada apenas como '
                          'referência.</p>')

        # Indicadores do ano de referência com menos de MIN_PARES pares com dado
        ano_ref = _ano_de_referencia(indicadores, media_setorial)
        limitados = [NOMES_INDICADORES[nome] for familia in FAMILIAS.values() for nome in familia
                     if media_setorial.get(ano_ref, {}).get(nome, {"n": 0})["n"] < MIN_PARES]
        if ano_ref and limitados:
            partes.append(f'<p class="aviso">Em {ano_ref}, os indicadores a seguir têm menos de '
                          f'{MIN_PARES} pares com dado e, por isso, não são classificados em '
                          f'relação ao setor: {_esc(", ".join(limitados))}.</p>')
        partes.append('<p class="meta">A referência é a média aritmética simples dos pares '
                      'que têm valor válido em cada ano. Ela é sensível a valores extremos e '
                      'não representa o setor inteiro.</p>')

    if falhas:
        itens = "".join(f"<li>{_esc(ticker)}: {_esc(motivo)}</li>" for ticker, motivo in falhas)
        partes.append(f'<p class="aviso">Concorrentes que não puderam ser utilizados:</p>'
                      f"<ul>{itens}</ul>")
    return "".join(partes)


# ----------------------------------------------------------------------
# Montagem dos blocos e função principal
# ----------------------------------------------------------------------

def montar_secoes(empresa, indicadores, media_setorial, interpretacao, falhas,
                  pares_utilizados=None):
    """
    Monta os blocos de HTML da análise, prontos para serem encaixados em uma página.

    É a ÚNICA fonte desses blocos: a interface web (templates/resultado.html)
    e o relatório HTML (gerar_relatorio) usam exatamente o mesmo conteúdo.

    Devolve um dicionário de textos HTML (já escapados) com as chaves:
    resumo, tabela, graficos, comparacao, interpretacao e notas.
    """
    pares = pares_utilizados or []
    resumo = "".join(f"<li>{_esc(frase)}</li>" for frase in interpretacao["resumo"])
    notas = "".join(f"<li>{_esc(nota)}</li>" for nota in
                    _notas_metodologicas(empresa, indicadores, media_setorial, falhas, pares))
    return {
        "resumo": f'<ul class="resumo">{resumo}</ul>',
        "tabela": _tabela_indicadores(indicadores, media_setorial),
        "graficos": _secao_graficos(indicadores, media_setorial),
        "comparacao": ('<div class="cartao-comparacao">'
                       + _secao_comparacao(indicadores, media_setorial, falhas, pares) + "</div>"),
        "interpretacao": _secao_interpretacao(interpretacao),
        "notas": f"<ul>{notas}</ul>",
    }


def gerar_relatorio(empresa, indicadores, media_setorial, interpretacao, falhas,
                    pasta_saida, pares_utilizados=None, integrantes=None):
    """
    Grava o relatório HTML autocontido e devolve o caminho do arquivo.

    empresa: dicionário do contrato (ticker, nome, setor, anos).
    indicadores: saída de calcular_indicadores(empresa).
    media_setorial: saída de calcular_media_setorial(); {} se não houver pares.
    interpretacao: saída de gerar_interpretacao().
    falhas: lista de (ticker, motivo) dos concorrentes que falharam.
    pasta_saida: pasta onde gravar (criada se não existir).
    pares_utilizados: (opcional) empresas dos pares usadas na média, para listá-las.
    integrantes: (opcional) nomes da dupla, exibidos no rodapé.

    Nome do arquivo: relatorio_<ticker sem .SA>_<AAAA-MM-DD>.html. Um relatório
    do mesmo dia e da mesma empresa é sobrescrito.
    """
    agora = datetime.now()
    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"relatorio_{empresa['ticker'].replace('.SA', '')}_{agora:%Y-%m-%d}.html"
    caminho = pasta / nome_arquivo

    secoes = montar_secoes(empresa, indicadores, media_setorial, interpretacao, falhas,
                           pares_utilizados)
    nomes_dupla = ", ".join(integrantes) if integrantes else "integrantes não informados"

    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Análise de demonstrações financeiras: {_esc(empresa['nome'])}</title>
<style>{_ler_css()}</style>
</head>
<body>
<header class="hero hero-relatorio">
<div class="container">
<p class="selo">Relatório de análise</p>
<h1>{_esc(empresa['nome'])}</h1>
<p class="hero-meta"><span class="ticker">{_esc(empresa['ticker'])}</span> {_esc(empresa['setor'])}</p>
<p class="hero-meta">Gerado em {agora:%d/%m/%Y às %H:%M} | Fonte dos dados: {_esc(FONTE_DOS_DADOS)}</p>
</div>
</header>
<main class="container">

<h2>1. Resumo geral</h2>
{secoes['resumo']}

<h2>2. Indicadores por ano</h2>
{secoes['tabela']}

<h2>3. Gráficos de evolução</h2>
{secoes['graficos']}

<h2>4. Comparação com empresas do setor</h2>
{secoes['comparacao']}

<h2>5. Interpretação</h2>
{secoes['interpretacao']}

<h2>6. Notas metodológicas e limitações</h2>
{secoes['notas']}

<footer>
<p>Disciplina: {_esc(DISCIPLINA)}.<br>Integrantes: {_esc(nomes_dupla)}.</p>
</footer>
</main>
</body>
</html>
"""
    caminho.write_text(pagina, encoding="utf-8")
    return caminho
