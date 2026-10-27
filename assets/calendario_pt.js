(function () {
  if (window.__calendarioPt) return;
  window.__calendarioPt = true;
  const mapa = {
    January: "Janeiro", February: "Fevereiro", March: "Março", April: "Abril", May: "Maio", June: "Junho",
    July: "Julho", August: "Agosto", September: "Setembro", October: "Outubro", November: "Novembro", December: "Dezembro",
    Su: "Dom", Mo: "Seg", Tu: "Ter", We: "Qua", Th: "Qui", Fr: "Sex", Sa: "Sáb",
  };
  function traduzir() {
    document.querySelectorAll('[data-baseweb="calendar"], [data-baseweb="popover"], [data-baseweb="menu"]').forEach((raiz) => {
      const it = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
      let no;
      while ((no = it.nextNode())) {
        const texto = no.nodeValue.trim();
        if (mapa[texto]) no.nodeValue = no.nodeValue.replace(texto, mapa[texto]);
      }
    });
  }
  new MutationObserver(traduzir).observe(document.body, { childList: true, subtree: true, characterData: true });
  traduzir();
})();
