"""
setores.py

MÓDULO DE SETORES E MENU.

Papel no fluxo: é a primeira etapa da aplicação. Define a lista FIXA de
setores e empresas disponíveis, pergunta ao usuário qual empresa analisar
e informa quais são as empresas comparáveis (concorrentes) dela.

Entradas : escolha do usuário no terminal (setor e depois empresa).
Saídas   : (ticker, nome, setor) da empresa escolhida e a lista de
           concorrentes do mesmo setor.

Este módulo NÃO contém lógica financeira. A lista de concorrentes é
escrita à mão, de propósito: não há detecção automática de concorrentes.

Observação: bancos, seguradoras e demais instituições financeiras ficaram
de fora, pois a estrutura contábil delas (sem estoque, sem ciclo
operacional) torna os indicadores deste trabalho pouco aplicáveis.
"""

# Setor em destaque: o da Localiza. É sempre a primeira opção do menu e
# a sugestão padrão (basta apertar Enter).
SETOR_DESTAQUE = "Locação de veículos e frotas"

# Dicionário {setor: [(ticker, nome da empresa), ...]}.
# A ORDEM importa: o dicionário é exibido na ordem em que está escrito,
# e a Localiza (RENT3.SA) é a primeira empresa do primeiro setor.
# Os tickers foram testados no yfinance (ver README, seção de limitações).
SETORES = {
    SETOR_DESTAQUE: [
        ("RENT3.SA", "Localiza&Co"),
        ("MOVI3.SA", "Movida"),
        ("VAMO3.SA", "Vamos"),
        ("SIMH3.SA", "Simpar"),   # grupo diversificado: comparável com cautela
    ],
    "Varejo": [
        ("LREN3.SA", "Lojas Renner"),
        ("AZZA3.SA", "Azzas 2154"),
        ("CEAB3.SA", "C&A Modas"),
        ("MGLU3.SA", "Magazine Luiza"),
    ],
    "Bens de capital e indústria": [
        ("WEGE3.SA", "WEG"),
        ("ROMI3.SA", "Indústrias Romi"),
        ("TUPY3.SA", "Tupy"),
    ],
    "Siderurgia e mineração": [
        ("VALE3.SA", "Vale"),
        ("GGBR4.SA", "Gerdau"),
        ("CSNA3.SA", "CSN"),
        ("USIM5.SA", "Usiminas"),
    ],
}


def _pedir_opcao(titulo, opcoes, padrao=None):
    """
    Mostra uma lista numerada e repete a pergunta até a resposta ser válida.

    titulo: texto exibido acima da lista.
    opcoes: lista de textos a exibir (a numeração começa em 1).
    padrao: número (base 1) escolhido se o usuário apertar só Enter,
            ou None para exigir uma resposta.

    Devolve o índice escolhido (base 0).
    """
    print(f"\n{titulo}")
    for numero, texto in enumerate(opcoes, start=1):
        marca = " (padrão)" if numero == padrao else ""
        print(f"  {numero}. {texto}{marca}")

    while True:
        resposta = input("Escolha uma opção: ").strip()
        if resposta == "" and padrao is not None:
            return padrao - 1
        if resposta.isdigit() and 1 <= int(resposta) <= len(opcoes):
            return int(resposta) - 1
        print(f"Opção inválida. Digite um número de 1 a {len(opcoes)}.")


def escolher_empresa():
    """
    Menu em duas etapas: primeiro o setor, depois a empresa.

    Entrada inválida repete a pergunta. Devolve (ticker, nome, setor).
    """
    nomes_setores = list(SETORES)
    indice_setor = _pedir_opcao("Setores disponíveis:", nomes_setores, padrao=1)
    setor = nomes_setores[indice_setor]

    empresas = SETORES[setor]
    textos = [f"{nome} ({ticker})" for ticker, nome in empresas]
    indice_empresa = _pedir_opcao(f"Empresas do setor '{setor}':", textos, padrao=1)
    ticker, nome = empresas[indice_empresa]
    return ticker, nome, setor


def obter_concorrentes(setor, ticker_excluido):
    """
    Devolve as empresas do setor, EXCETO a analisada.

    setor: chave de SETORES. Se o setor não existir, devolve lista vazia.
    ticker_excluido: ticker da empresa em análise (ela não pode entrar na
                     própria referência setorial).

    Retorno: lista de tuplas (ticker, nome).
    """
    return [(ticker, nome) for ticker, nome in SETORES.get(setor, [])
            if ticker != ticker_excluido]


def buscar_empresa_por_ticker(ticker):
    """
    Localiza um ticker na lista fixa (usado pelo modo --ticker).

    Devolve (ticker, nome, setor) ou None se o ticker não estiver na lista.
    A comparação ignora maiúsculas/minúsculas.
    """
    for setor, empresas in SETORES.items():
        for ticker_lista, nome in empresas:
            if ticker_lista.upper() == ticker.upper():
                return ticker_lista, nome, setor
    return None


# Teste rápido: python setores.py
if __name__ == "__main__":
    escolhida = escolher_empresa()
    print("\nEscolhida:", escolhida)
    print("Concorrentes:", obter_concorrentes(escolhida[2], escolhida[0]))
