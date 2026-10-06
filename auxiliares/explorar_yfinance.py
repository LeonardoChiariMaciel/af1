"""
explorar_yfinance.py

SCRIPT DE DIAGNÓSTICO (não faz parte do programa final).

Objetivo: descobrir como o yfinance entrega as demonstrações de empresas
reais, para depois escrever o módulo de captura com base no que existe
de fato. Para cada empresa, mostra:
  - quais anos vêm no balanço e na DRE;
  - para cada uma das 11 contas do nosso contrato, qual linha da fonte
    foi encontrada e qual o valor do ano mais recente.

Como rodar (no terminal, dentro da pasta do projeto):
    pip install yfinance
    python explorar_yfinance.py

Também grava, para cada empresa, um arquivo yfinance_linhas_<ticker>.txt
com TODOS os nomes de linhas que a fonte entregou.
"""

# Empresas de teste (pode trocar). O sufixo .SA indica a bolsa brasileira.
TICKERS_TESTE = ["WEGE3.SA", "LREN3.SA", "TOTS3.SA"]

# Para cada conta do nosso contrato, os nomes que ESPERAMOS encontrar na
# fonte (hipóteses). O primeiro nome que existir é o usado.
# Este dicionário será reaproveitado no módulo de captura final.
MAPA_CONTAS_CANDIDATAS = {
    # Balanço patrimonial
    "ativo_circulante": ["Current Assets"],
    "passivo_circulante": ["Current Liabilities"],
    "estoque": ["Inventory"],
    "contas_a_receber": ["Accounts Receivable", "Receivables"],
    "fornecedores": ["Accounts Payable", "Payables"],
    "ativo_total": ["Total Assets"],
    "passivo_total": ["Total Liabilities Net Minority Interest"],
    "patrimonio_liquido": ["Stockholders Equity", "Common Stock Equity"],
    # DRE
    "receita_liquida": ["Total Revenue", "Operating Revenue"],
    "cmv": ["Cost Of Revenue"],
    "lucro_liquido": ["Net Income", "Net Income Common Stockholders"],
}


def procurar_conta(tabelas, candidatos):
    """
    Procura, nas tabelas dadas, a primeira linha cujo nome esteja na
    lista de candidatos.

    Devolve (nome_encontrado, tabela) ou (None, None) se nenhuma existir.
    """
    for nome in candidatos:
        for tabela in tabelas:
            if tabela is not None and not tabela.empty and nome in tabela.index:
                return nome, tabela
    return None, None


def anos_da_tabela(tabela):
    """Lista os anos (colunas) de uma tabela do yfinance, do mais novo ao mais antigo."""
    if tabela is None or tabela.empty:
        return []
    return sorted({coluna.year for coluna in tabela.columns}, reverse=True)


def valor_mais_recente(tabela, nome_linha):
    """Valor da linha na coluna mais recente (a de data máxima)."""
    coluna_recente = max(tabela.columns)
    return tabela.loc[nome_linha, coluna_recente]


def explorar(ticker):
    """Baixa as demonstrações de um ticker e imprime o diagnóstico."""
    import yfinance as yf  # importado aqui para as funções acima serem testáveis sem a biblioteca

    print(f"\n=== {ticker} ===")
    try:
        empresa = yf.Ticker(ticker)
        balanco = empresa.balance_sheet
        # Versões antigas do yfinance chamam a DRE de 'financials'
        dre = getattr(empresa, "income_stmt", None)
        if dre is None:
            dre = empresa.financials
    except Exception as erro:
        print(f"Falha ao baixar os dados: {erro}")
        return

    if balanco is None or balanco.empty or dre is None or dre.empty:
        print("A fonte não devolveu balanço e/ou DRE para este ticker.")
        return

    print("Anos no balanço:", anos_da_tabela(balanco))
    print("Anos na DRE    :", anos_da_tabela(dre))
    print()
    print(f"{'conta do contrato':<20} | {'linha encontrada na fonte':<42} | valor (ano mais recente)")
    print("-" * 100)

    for conta, candidatos in MAPA_CONTAS_CANDIDATAS.items():
        nome, tabela = procurar_conta([balanco, dre], candidatos)
        if nome is None:
            print(f"{conta:<20} | {'NÃO ENCONTRADA':<42} | -")
        else:
            valor = valor_mais_recente(tabela, nome)
            texto = "vazio (NaN)" if valor != valor else f"{valor:,.0f}"  # NaN != NaN
            print(f"{conta:<20} | {nome:<42} | {texto}")

    # Grava TODOS os nomes de linhas entregues, para consulta
    arquivo = f"yfinance_linhas_{ticker}.txt"
    with open(arquivo, "w", encoding="utf-8") as f:
        f.write("BALANÇO\n")
        f.writelines(f"  {linha}\n" for linha in balanco.index)
        f.write("\nDRE\n")
        f.writelines(f"  {linha}\n" for linha in dre.index)
    print(f"\n(Todas as linhas entregues foram gravadas em {arquivo})")


if __name__ == "__main__":
    for ticker in TICKERS_TESTE:
        explorar(ticker)