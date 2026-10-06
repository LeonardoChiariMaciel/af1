"""
interpretacao.py

MÓDULO DE INTERPRETAÇÃO.

Papel no fluxo: transforma os números dos indicadores em frases
descritivas, em português, para o relatório.

Entradas : empresa (contrato), indicadores da empresa, média setorial.
Saídas   : gerar_interpretacao() devolve
              {
                "familias": {nome_da_familia: {"notas": [str], "itens": [str]}},
                "resumo":   [str],
              }

Princípios (importantes para a defesa do trabalho):
  - A linguagem é DESCRITIVA e cautelosa. O módulo diz o que aconteceu com
    o indicador (aumentou, diminuiu, ficou estável) e, quando faz sentido,
    qual é o sentido que tende a ser favorável em uma leitura simplificada.
  - NÃO há recomendação de compra, venda ou manutenção de ações.
  - NÃO há faixas absolutas (ex.: "liquidez acima de 1 é boa"), pois o
    trabalho não adotou uma referência bibliográfica para isso. Usam-se
    apenas a evolução da própria empresa e a comparação com os pares.
  - Valor None nunca é comparado nem tratado como zero.
"""

from indicadores import formatar_indicador
from referencia_setorial import MIN_PARES
from setores import SETOR_DESTAQUE

# ----------------------------------------------------------------------
# PARÂMETROS METODOLÓGICOS DO TRABALHO
# ----------------------------------------------------------------------

# Tolerância relativa usada para decidir se uma diferença é "relevante".
# Duas situações usam a mesma regra:
#   1) variação entre dois anos da própria empresa;
#   2) valor da empresa contra a média dos pares.
# Se |diferença| <= 10% do valor de referência, o texto diz "relativamente
# estável" (ou "aproximadamente em linha com a média").
# ATENÇÃO: os 10% são uma DECISÃO METODOLÓGICA desta aplicação, para não
# tratar diferenças pequenas como economicamente relevantes. Não é regra
# de livro nem regra universal de finanças.
TOLERANCIA_RELATIVA = 0.10

# Sentido que TENDE a ser favorável em uma leitura financeira simplificada.
#   "maior"   : aumento tende a ser favorável
#   "menor"   : redução tende a ser favorável
#   "depende" : não há sentido único; o texto só descreve o movimento
# É uma convenção de leitura, sempre sujeita ao contexto da empresa.
TENDENCIA_GERAL = {
    # Liquidez maior pode indicar maior capacidade relativa de pagar
    # obrigações de curto prazo.
    "liquidez_corrente": "maior",
    "liquidez_seca": "maior",
    # Menor endividamento tende a reduzir a dependência de capital de
    # terceiros (e o risco de não conseguir pagar os credores).
    "endividamento_geral": "menor",
    "divida_sobre_patrimonio": "menor",
    # Maior margem tende a indicar mais lucro para cada real vendido; maior
    # ROA e ROE, mais retorno sobre ativos e sobre o capital dos sócios.
    "margem_liquida": "maior",
    "roa": "maior",
    "roe": "maior",
    # PMR menor tende a acelerar a entrada de caixa.
    "pmr": "menor",
    # PME menor pode representar maior giro de estoque, mas depende do
    # modelo de negócio (há empresas que operam com estoque alto de propósito).
    "pme": "menor",
    # PMP maior pode aliviar o caixa, mas depende da relação com os
    # fornecedores (prazos muito longos podem ter custo embutido). Por isso
    # NÃO é chamado automaticamente de melhor.
    "pmp": "depende",
    # Ciclos menores tendem a reduzir o capital preso na operação, mas a
    # leitura depende da atividade da empresa.
    "ciclo_operacional": "menor",
    "ciclo_financeiro": "menor",
}

# Famílias de indicadores (a mesma divisão de indicadores.py)
FAMILIAS = {
    "Liquidez": ("liquidez_corrente", "liquidez_seca"),
    "Endividamento": ("endividamento_geral", "divida_sobre_patrimonio"),
    "Rentabilidade": ("margem_liquida", "roa", "roe"),
    "Atividade": ("pmr", "pme", "pmp", "ciclo_operacional", "ciclo_financeiro"),
}

# Nomes para exibição (tabelas, gráficos e textos)
NOMES_INDICADORES = {
    "liquidez_corrente": "Liquidez corrente",
    "liquidez_seca": "Liquidez seca",
    "endividamento_geral": "Endividamento geral",
    "divida_sobre_patrimonio": "Dívida sobre patrimônio",
    "margem_liquida": "Margem líquida",
    "roa": "ROA",
    "roe": "ROE",
    "pmr": "Prazo médio de recebimento (PMR)",
    "pme": "Prazo médio de estocagem (PME)",
    "pmp": "Prazo médio de pagamento (PMP)",
    "ciclo_operacional": "Ciclo operacional",
    "ciclo_financeiro": "Ciclo financeiro",
}

# Indicadores de atividade que dependem de estoque / ciclo de mercadorias
INDICADORES_DE_ESTOQUE = ("pme", "ciclo_operacional", "ciclo_financeiro", "liquidez_seca")

NAO_DISPONIVEL = "Não disponível."
NAO_REPRESENTATIVO = "Indicador não disponível ou pouco representativo para esta empresa."

# ----------------------------------------------------------------------
# Comparações elementares
# ----------------------------------------------------------------------


def _dentro_da_tolerancia(valor, referencia):
    """True se |valor - referência| <= TOLERANCIA_RELATIVA * |referência|."""
    if referencia == 0:
        return valor == 0
    return abs(valor - referencia) <= TOLERANCIA_RELATIVA * abs(referencia)


def classificar_variacao(valor_antigo, valor_novo):
    """
    Descreve a variação entre dois valores da própria empresa.

    Devolve "aumentou", "diminuiu", "estavel" ou None (se algum valor
    for None: não há como comparar). "estavel" significa variação dentro
    de TOLERANCIA_RELATIVA do valor antigo.
    """
    if valor_antigo is None or valor_novo is None:
        return None
    if _dentro_da_tolerancia(valor_novo, valor_antigo):
        return "estavel"
    return "aumentou" if valor_novo > valor_antigo else "diminuiu"


def comparar_com_media(valor, media):
    """
    Compara o valor da empresa com a média dos pares.

    Devolve "acima", "abaixo", "em linha" ou None (se algum for None).
    "em linha" = diferença dentro de TOLERANCIA_RELATIVA da média.
    """
    if valor is None or media is None:
        return None
    if _dentro_da_tolerancia(valor, media):
        return "em linha"
    return "acima" if valor > media else "abaixo"


def classificar_sentido(nome, movimento):
    """
    Cruza um movimento ("aumentou"/"diminuiu"/"acima"/"abaixo") com
    TENDENCIA_GERAL. Devolve "favoravel", "nao_favoravel" ou None
    (sem leitura direcional: estável, em linha ou indicador "depende").
    """
    tendencia = TENDENCIA_GERAL[nome]
    if tendencia == "depende" or movimento in (None, "estavel", "em linha"):
        return None
    subiu = movimento in ("aumentou", "acima")
    if tendencia == "maior":
        return "favoravel" if subiu else "nao_favoravel"
    return "favoravel" if not subiu else "nao_favoravel"


# ----------------------------------------------------------------------
# Frases
# ----------------------------------------------------------------------

_VERBO_VARIACAO = {
    "aumentou": "aumentou",
    "diminuiu": "diminuiu",
    "estavel": "permaneceu relativamente estável",
}
_COMPLEMENTO_SENTIDO = {
    "favoravel": " (movimento geralmente favorável sob a ótica deste indicador)",
    "nao_favoravel": " (movimento oposto ao geralmente favorável sob a ótica deste indicador)",
    None: "",
}


def _patrimonio_nao_positivo(empresa, ano):
    """True se o patrimônio líquido do ano existe e é zero ou negativo."""
    patrimonio = empresa["anos"].get(ano, {}).get("patrimonio_liquido")
    return patrimonio is not None and patrimonio <= 0


def _frase_evolucao(nome, indicadores, ano_antigo, ano_novo, rotulo):
    """
    Frase comparando dois anos da própria empresa.

    rotulo: como chamar a comparação ("ano anterior" ou "primeiro ano").
    Devolve None se não houver como comparar (um dos anos sem dado).
    """
    antigo = indicadores[ano_antigo][nome]
    novo = indicadores[ano_novo][nome]
    movimento = classificar_variacao(antigo, novo)
    if movimento is None:
        return f"Sem dado em {ano_antigo} para comparação com o {rotulo}."
    sentido = classificar_sentido(nome, movimento)
    return (f"Em relação ao {rotulo} ({ano_antigo}: {formatar_indicador(nome, antigo)}), "
            f"o indicador {_VERBO_VARIACAO[movimento]}{_COMPLEMENTO_SENTIDO[sentido]}.")


def _frase_setor(nome, valor, ano, media_setorial):
    """
    Frase comparando a empresa com a média dos pares no ano dado.

    Só classifica (acima/abaixo/em linha) se n >= MIN_PARES; com menos
    pares apenas informa que a referência é limitada.
    """
    info = media_setorial.get(ano, {}).get(nome)
    if info is None or info["media"] is None:
        return f"Sem referência setorial disponível para {ano}."

    media, n = info["media"], info["n"]
    texto_media = f"{formatar_indicador(nome, media)}, n = {n}"
    if n < MIN_PARES:
        return (f"Referência setorial limitada em {ano}: apenas {n} par com dado "
                f"(média: {texto_media}). Não há base para classificar a empresa "
                f"em relação ao setor.")

    posicao = comparar_com_media(valor, media)
    descricao = {"acima": "acima da média", "abaixo": "abaixo da média",
                 "em linha": "aproximadamente em linha com a média"}[posicao]
    sentido = classificar_sentido(nome, posicao)
    complemento = {"favoravel": " (sentido geralmente favorável)",
                   "nao_favoravel": " (sentido oposto ao geralmente favorável)",
                   None: ""}[sentido]
    return (f"Em {ano}, o valor da empresa está {descricao} dos pares "
            f"({texto_media}){complemento}.")


def interpretar_indicador(nome, empresa, indicadores, media_setorial):
    """
    Texto completo de UM indicador: valor atual, evolução própria e setor.

    Casos especiais:
      - valor None: "Não disponível." (sem comparar nada);
      - patrimônio líquido zero/negativo: explica em vez de classificar.
    """
    anos = sorted(indicadores)
    ultimo = anos[-1]
    valor = indicadores[ultimo][nome]
    rotulo = NOMES_INDICADORES[nome]

    # Patrimônio líquido zero ou negativo: ROE fica None (indicadores.py) e
    # dívida/patrimônio perde o sentido usual (resultado negativo).
    if nome in ("roe", "divida_sobre_patrimonio") and _patrimonio_nao_positivo(empresa, ultimo):
        return (f"{rotulo}: o patrimônio líquido de {ultimo} é zero ou negativo, "
                f"situação em que este indicador é de difícil interpretação "
                f"(o resultado pode ser nulo ou negativo e não é comparável). "
                f"Por isso ele não é classificado como favorável ou desfavorável.")

    if valor is None:
        complemento = f" {NAO_REPRESENTATIVO}" if nome in INDICADORES_DE_ESTOQUE else ""
        return f"{rotulo}: {NAO_DISPONIVEL}{complemento}"

    # Se algum ano comparado tem patrimônio não positivo, a comparação de
    # dívida/patrimônio entre anos também seria enganosa.
    if nome == "divida_sobre_patrimonio" and any(
            _patrimonio_nao_positivo(empresa, ano) for ano in anos):
        return (f"{rotulo}: {formatar_indicador(nome, valor)} em {ultimo}. Em ao menos um "
                f"ano da série o patrimônio líquido é zero ou negativo; por isso "
                f"as comparações deste indicador entre anos não são feitas.")

    partes = [f"{rotulo}: {formatar_indicador(nome, valor)} em {ultimo}."]

    if len(anos) >= 2:
        partes.append(_frase_evolucao(nome, indicadores, anos[-2], ultimo, "ano anterior"))
    if len(anos) >= 3:
        partes.append(_frase_evolucao(nome, indicadores, anos[0], ultimo, "primeiro ano"))
    if len(anos) == 1:
        partes.append("Há apenas um ano de dados; não é possível analisar a evolução.")

    partes.append(_frase_setor(nome, valor, ultimo, media_setorial))
    return " ".join(partes)


def _notas_da_familia(familia, empresa):
    """Avisos de contexto que valem para a família inteira."""
    notas = []
    if familia == "Atividade":
        notas.append("PMP maior pode aliviar o caixa, mas depende da relação com os "
                     "fornecedores; por isso o texto apenas descreve o movimento do PMP, "
                     "sem chamá-lo de melhor ou pior.")
        if empresa["setor"] == SETOR_DESTAQUE:
            notas.append("Em locadoras de veículos a frota fica no imobilizado, e não em "
                         "estoque de mercadorias. Por isso PME e os ciclos têm leitura "
                         "limitada (ou ficam indisponíveis) e devem ser interpretados com "
                         "cautela, considerando o modelo de negócio.")
    if familia == "Liquidez" and empresa["setor"] == SETOR_DESTAQUE:
        notas.append("A liquidez seca depende da conta de estoque, que pode não existir "
                     "para locadoras; quando ausente, o indicador fica indisponível.")
    if familia == "Endividamento":
        notas.append("O endividamento usa o passivo total (todas as obrigações), e não "
                     "apenas a dívida financeira. Empresas com grandes frotas costumam "
                     "operar com alavancagem elevada; compare sempre com a própria "
                     "evolução e com pares do mesmo modelo de negócio. A média dos pares "
                     "é simples e pode ser puxada por uma empresa muito alavancada.")
    return notas


# ----------------------------------------------------------------------
# Resumo geral
# ----------------------------------------------------------------------


def gerar_resumo(empresa, indicadores, media_setorial):
    """
    Resumo curto: conta quantos indicadores se moveram em cada sentido
    (último ano contra o anterior) e quantos estão acima/abaixo dos pares.
    Descreve movimentos; não recomenda nada.
    """
    anos = sorted(indicadores)
    ultimo = anos[-1]
    resumo = []

    if len(anos) >= 2:
        anterior = anos[-2]
        favoraveis, opostos, estaveis, neutros, sem_dado = [], [], [], [], []
        for nome in TENDENCIA_GERAL:
            rotulo = NOMES_INDICADORES[nome]
            movimento = classificar_variacao(indicadores[anterior][nome],
                                             indicadores[ultimo][nome])
            if movimento is None:
                sem_dado.append(rotulo)
            elif movimento == "estavel":
                estaveis.append(rotulo)
            else:
                sentido = classificar_sentido(nome, movimento)
                {"favoravel": favoraveis, "nao_favoravel": opostos, None: neutros}[sentido].append(rotulo)

        resumo.append(f"Entre {anterior} e {ultimo}, {len(favoraveis)} indicador(es) tiveram "
                      f"movimento geralmente favorável: {', '.join(favoraveis) or 'nenhum'}.")
        resumo.append(f"{len(opostos)} indicador(es) se moveram no sentido oposto ao "
                      f"geralmente favorável: {', '.join(opostos) or 'nenhum'}.")
        if estaveis:
            resumo.append(f"Permaneceram relativamente estáveis: {', '.join(estaveis)}.")
        if neutros:
            resumo.append(f"Variaram sem leitura direcional (dependem do contexto): {', '.join(neutros)}.")
        if sem_dado:
            resumo.append(f"Sem dado suficiente para comparar: {', '.join(sem_dado)}.")
    else:
        resumo.append(f"Há apenas um ano de dados ({ultimo}); a evolução não pôde ser analisada.")

    # Posição frente aos pares (somente onde há pares suficientes)
    posicoes = {"acima": [], "abaixo": [], "em linha": []}
    limitados = 0
    for nome in TENDENCIA_GERAL:
        info = media_setorial.get(ultimo, {}).get(nome)
        valor = indicadores[ultimo][nome]
        if info is None or info["media"] is None or valor is None:
            continue
        if info["n"] < MIN_PARES:
            limitados += 1
            continue
        if nome in ("roe", "divida_sobre_patrimonio") and _patrimonio_nao_positivo(empresa, ultimo):
            continue
        posicoes[comparar_com_media(valor, info["media"])].append(NOMES_INDICADORES[nome])

    if any(posicoes.values()):
        resumo.append(
            f"Em {ultimo}, frente à média dos pares: acima em {len(posicoes['acima'])} "
            f"indicador(es), abaixo em {len(posicoes['abaixo'])} e aproximadamente em linha "
            f"em {len(posicoes['em linha'])}. A referência setorial tem poucas empresas e "
            f"deve ser lida com cautela.")
    else:
        resumo.append("Não houve pares suficientes para uma comparação setorial; a análise "
                      "se baseia na evolução da própria empresa.")
    if limitados:
        resumo.append(f"{limitados} indicador(es) tiveram referência setorial limitada "
                      f"(menos de {MIN_PARES} pares com dado) e não foram classificados.")

    resumo.append("Este texto descreve movimentos dos indicadores com fins acadêmicos e "
                  "não constitui recomendação de investimento.")
    return resumo


def gerar_interpretacao(empresa, indicadores, media_setorial):
    """
    Gera a interpretação completa.

    empresa: dicionário no formato do contrato.
    indicadores: saída de calcular_indicadores(empresa).
    media_setorial: saída de calcular_media_setorial(pares); {} se não houver pares.

    Devolve {"familias": {família: {"notas": [...], "itens": [...]}}, "resumo": [...]}.
    """
    familias = {}
    for familia, nomes in FAMILIAS.items():
        familias[familia] = {
            "notas": _notas_da_familia(familia, empresa),
            "itens": [interpretar_indicador(nome, empresa, indicadores, media_setorial)
                      for nome in nomes],
        }
    return {"familias": familias,
            "resumo": gerar_resumo(empresa, indicadores, media_setorial)}
