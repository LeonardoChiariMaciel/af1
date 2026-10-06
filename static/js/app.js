/*
 * app.js
 *
 * JavaScript da interface. Não calcula nada financeiro. Faz apenas:
 *   1) tela inicial: mostra só as empresas do setor escolhido e exibe o
 *      andamento enquanto o servidor captura os dados;
 *   2) tela de resultados: abas dos gráficos e destaque da seção visível
 *      no menu superior.
 *
 * A lista de setores e empresas vem do Python (setores.py) já escrita no
 * HTML; este arquivo não repete essa lista. Sem JavaScript a página continua
 * funcionando: as empresas aparecem todas juntas e os gráficos, um abaixo do outro.
 */

(function () {
  // ---------------------------------------------------------------
  // Tela inicial
  // ---------------------------------------------------------------
  var seletorSetor = document.getElementById("setor");
  var seletorEmpresa = document.getElementById("ticker");
  var formulario = document.getElementById("form-analise");
  var carregando = document.getElementById("carregando");
  var botao = document.getElementById("botao-analisar");
  var etapas = document.querySelectorAll("#etapas li");
  var cronometro = null;

  // Mostra só as empresas do setor escolhido. Se a empresa já selecionada
  // (marcada pelo servidor) é desse setor, ela é mantida; senão, vale a primeira.
  function filtrarEmpresas() {
    var setor = seletorSetor.value;
    var atual = seletorEmpresa.options[seletorEmpresa.selectedIndex];
    var manter = atual && atual.getAttribute("data-setor") === setor;
    var primeira = null;
    Array.prototype.forEach.call(seletorEmpresa.options, function (opcao) {
      var visivel = opcao.getAttribute("data-setor") === setor;
      opcao.hidden = !visivel;
      opcao.disabled = !visivel;
      if (visivel && primeira === null) { primeira = opcao; }
    });
    if (!manter && primeira !== null) { primeira.selected = true; }
  }

  if (seletorSetor && seletorEmpresa) {
    seletorSetor.addEventListener("change", filtrarEmpresas);
    filtrarEmpresas();
  }

  // Marca a etapa atual na lista de andamento. As etapas trocam com o tempo
  // e são apenas indicativas: o servidor faz tudo e só responde ao terminar.
  function marcarEtapa(indice) {
    Array.prototype.forEach.call(etapas, function (item, posicao) {
      item.className = posicao < indice ? "feita" : (posicao === indice ? "atual" : "");
    });
  }

  if (formulario && carregando) {
    formulario.addEventListener("submit", function () {
      var indice = 0;
      marcarEtapa(0);
      carregando.classList.add("ativo");
      botao.disabled = true;
      cronometro = window.setInterval(function () {
        indice = Math.min(indice + 1, etapas.length - 1);
        marcarEtapa(indice);
      }, 6000);
    });
  }

  // Ao voltar pelo botão do navegador, a tela de carregamento não deve reaparecer
  window.addEventListener("pageshow", function () {
    if (carregando) { carregando.classList.remove("ativo"); }
    if (botao) { botao.disabled = false; }
    if (cronometro) { window.clearInterval(cronometro); }
  });

  // ---------------------------------------------------------------
  // Tela de resultados: abas dos gráficos
  // ---------------------------------------------------------------
  var area = document.getElementById("area-graficos");
  if (area) {
    var figuras = area.querySelectorAll("figure.grafico");
    if (figuras.length > 1) {
      var barraAbas = document.createElement("div");
      barraAbas.className = "abas";
      barraAbas.setAttribute("role", "tablist");

      var selecionar = function (indice) {
        Array.prototype.forEach.call(figuras, function (figura, posicao) {
          figura.hidden = posicao !== indice;
          if (posicao === indice) {
            figura.classList.remove("entrando");
            void figura.offsetWidth;            // reinicia a animação
            figura.classList.add("entrando");
          }
        });
        Array.prototype.forEach.call(barraAbas.children, function (aba, posicao) {
          aba.setAttribute("aria-selected", posicao === indice ? "true" : "false");
        });
      };

      Array.prototype.forEach.call(figuras, function (figura, posicao) {
        var aba = document.createElement("button");
        aba.type = "button";
        aba.className = "aba";
        aba.setAttribute("role", "tab");
        aba.textContent = figura.getAttribute("data-familia");
        aba.addEventListener("click", function () { selecionar(posicao); });
        barraAbas.appendChild(aba);
      });
      area.insertBefore(barraAbas, area.firstChild);
      selecionar(0);
    }
  }

  // ---------------------------------------------------------------
  // Tela de resultados: destaca no menu a seção que está na tela
  // ---------------------------------------------------------------
  var links = document.querySelectorAll(".subnav a");
  if (links.length && "IntersectionObserver" in window) {
    var porId = {};
    Array.prototype.forEach.call(links, function (link) {
      porId[link.getAttribute("href").slice(1)] = link;
    });
    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (entrada.isIntersecting) {
          Array.prototype.forEach.call(links, function (l) { l.classList.remove("ativo"); });
          porId[entrada.target.id].classList.add("ativo");
        }
      });
    }, { rootMargin: "-130px 0px -60% 0px" });
    Object.keys(porId).forEach(function (id) {
      var secao = document.getElementById(id);
      if (secao) { observador.observe(secao); }
    });
  }
})();
