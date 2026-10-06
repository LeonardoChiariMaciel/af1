# Análise de demonstrações financeiras com Python

Trabalho 1 de **Administração Financeira (CAD 167)**, Sistemas de Informação, UFMG
(professor Bruno Pérez Ferreira).

Integrantes: Leonardo Chiari e Rodrigo Prates (editáveis em `INTEGRANTES`, no topo do `main.py`).

## Sobre

O programa é uma aplicação web **local** (Flask): roda na máquina do usuário e é usada
pelo navegador. Ele captura as demonstrações financeiras anuais de uma empresa
brasileira, calcula 12 indicadores de Administração Financeira, analisa a evolução ao
longo dos anos, compara com empresas do mesmo setor, mostra tudo na tela e gera um
relatório HTML.

- **Tema:** análise de demonstrações financeiras (liquidez, endividamento,
  rentabilidade e atividade/prazos médios).
- **Empresa em destaque:** Localiza&Co (`RENT3.SA`), locadora de veículos.
- **Fonte dos dados:** Yahoo Finance, pela biblioteca `yfinance`.
- O programa **não** faz recomendação de investimento.

Fluxo: `navegador -> Flask -> captura (yfinance) -> indicadores -> média dos concorrentes -> interpretação -> tela de resultados -> relatório HTML`.

## Requisitos

- Python 3.10 ou superior (teste final feito com **Python 3.13.3**, Windows 11).
- **Conexão com a internet** durante a execução (os dados são capturados online).
- Dependências: `yfinance`, `pandas`, `matplotlib` (ver `requirements.txt`).

## Instalação

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (cmd):         .venv\Scripts\activate.bat
# Linux / macOS:         source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

O terminal mostra `Acesse: http://127.0.0.1:5000` e o navegador é aberto
automaticamente (se não abrir, copie o endereço para o navegador). Depois:

1. escolha o **setor** e a **empresa** (a Localiza vem selecionada);
2. clique em **Analisar empresa** e aguarde (a tela mostra o andamento);
3. veja resumo, tabela de indicadores, gráficos, comparação com o setor,
   interpretação e a seção de metodologia e limitações;
4. clique em **Gerar relatório** para baixar o relatório HTML.

Para encerrar, pressione `Ctrl+C` no terminal. Para iniciar sem abrir o navegador:
`python main.py --nao-abrir`. O servidor só aceita conexões da própria máquina
(`127.0.0.1`); nada é publicado na internet. A internet é necessária apenas para
capturar os dados no Yahoo Finance: a interface em si não carrega nada externo.

Testes automatizados (rodam offline):

```bash
python -m unittest discover -s testes -v
```

## Saída

São duas coisas distintas:

- **A interface web**, usada para escolher a empresa e visualizar os resultados.
- **O relatório**, arquivo gerado a partir daquela análise, para registro e entrega.
  O botão **Gerar relatório** baixa o arquivo e também o grava na pasta `relatorios/`
  (criada automaticamente) com o nome `relatorio_<ticker>_<data>.html`. É um único
  arquivo, com CSS e gráficos embutidos, que abre depois sem internet. Um relatório da
  mesma empresa no mesmo dia é sobrescrito.

Em `exemplo/relatorio_RENT3_exemplo.html` há uma amostra de uma execução real; ela
serve só para consulta e **não é usada pelo programa**.

## Fonte dos dados e falhas

- Todos os dados vêm do Yahoo Finance em cada execução. Não há dados embutidos
  no código nem modo de demonstração.
- Se a fonte ou a internet falharem, a própria tela mostra uma mensagem de erro clara
  (sem traceback). Falhas temporárias da fonte podem impedir a análise; basta tentar
  novamente.
- Se um **concorrente** falhar, ele é descartado, o motivo aparece na página e no
  relatório, e a análise continua com os demais.
- As análises feitas ficam guardadas só na memória do servidor, para o botão
  **Gerar relatório** não precisar capturar tudo de novo. Não há cache em disco nem
  dados de reserva.
- Antivírus que inspecionam HTTPS (por exemplo, o Avast) podem causar erro de
  certificado SSL, e o `yfinance` então devolve tabelas vazias. Nesse caso,
  desative a inspeção de HTTPS do antivírus ou aponte a variável de ambiente
  `CURL_CA_BUNDLE` para um arquivo de certificados que inclua o do antivírus.

## Estrutura

| Arquivo | Papel |
|---|---|
| `main.py` | servidor Flask local: rotas, fluxo da análise e inicialização |
| `templates/` | páginas HTML (`base`, `index`, `resultado`) |
| `static/` | `css/style.css` (também embutido no relatório) e `js/app.js` |
| `setores.py` | lista fixa de setores e empresas; menu |
| `captura.py` | captura via `yfinance` e tradução para o contrato |
| `contrato_dados.py` | formato dos dados entre módulos |
| `indicadores.py` | os 12 indicadores e a formatação |
| `referencia_setorial.py` | captura dos concorrentes e média setorial |
| `interpretacao.py` | textos descritivos a partir dos indicadores |
| `relatorio.py` | blocos de HTML e gráficos (usados pela tela e pelo relatório) |
| `auxiliares/explorar_yfinance.py` | script de diagnóstico (fora do programa final) |
| `testes/` | testes automatizados |

## Simplificações e limitações

- **365 dias** no ano para os prazos médios (constante `DIAS_NO_ANO`). É uma
  premissa metodológica: existem as duas convenções (365, ano civil, e 360, ano
  comercial) e não foi confirmada qual a disciplina adota. Para trocar, basta
  alterar essa constante em `indicadores.py`.
- **Saldos de fim de ano** (e não médias) em ROA, ROE e prazos médios.
- **PMP calculado sobre o CMV**, e não sobre as compras.
- **Passivo total** usado como dívida (endividamento e dívida/patrimônio). A dívida
  financeira (`Total Debt`) existe na fonte para Localiza e pares, mas não foi
  incluída, pois exige alterar o contrato de dados.
- **Patrimônio líquido dos controladores**; o ROE é `None` se o patrimônio for
  zero ou negativo.
- **Dados ausentes** permanecem `None` e aparecem como "Não disponível". Localiza e
  Movida não têm estoque na fonte, então liquidez seca, PME e os ciclos ficam
  indisponíveis; em locadoras a frota está no imobilizado, e esses indicadores
  têm leitura limitada.
- **Poucos pares:** a referência é a média simples dos concorrentes de uma lista
  fixa. Com menos de `MIN_PARES = 2` empresas com dado, não há comparação setorial.
  A média é sensível a valores extremos. A Simpar é um grupo diversificado, comparável
  só com cautela. A série de atividade da Vamos (VAMO3) tem uma quebra entre 2022 e
  2023 (o CMV cai mais de 50%), possivelmente por mudança de classificação na fonte;
  isso afeta a média de PME e ciclos.
- **Tolerância de 10%** (`TOLERANCIA_RELATIVA`) para considerar estável ou em linha:
  decisão metodológica do trabalho, não regra de finanças.
- **Sem faixas absolutas** de "bom" ou "ruim": não foi adotada referência
  bibliográfica para isso.
- **Comparabilidade histórica da Localiza:** a combinação de negócios com a Unidas foi
  concluída em 1º de julho de 2022 (data informada pelas companhias e noticiada pela
  imprensa, por exemplo
  [Money Times](https://www.moneytimes.com.br/fechamento-da-fusao-entre-localiza-rent3-e-unidas-lcam3-vai-acontecer-em-1o-de-julho)).
  Os resultados de 2022 tendem a refletir a operação combinada só em parte do ano, e
  variações entre anos podem refletir mudanças de estrutura, e não crescimento orgânico.
- Os números seguem a classificação do Yahoo Finance e podem diferir das
  demonstrações originais. A fonte entrega, no máximo, 4 anos utilizáveis
  (2022 a 2025 na última verificação); a coluna de 2021 vem quase vazia e é descartada.
- Os indicadores são exibidos com ponto decimal (ex.: `1.20`), conforme `formatar_indicador`.

## Como o projeto atende aos critérios do trabalho

| Critério | Onde |
|---|---|
| Execução da aplicação | `python main.py` e a interface no navegador; README e teste em ambiente virtual limpo |
| Captura de dados | `captura.py` e `yfinance` (dados reais, sem fallback) |
| Descrição nos comentários | todos os arquivos têm cabeçalho, docstrings e as fórmulas explicadas |
| Relatórios | `relatorio.py` e a pasta `relatorios/` |
