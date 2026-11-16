// Esconde o botão do topo enquanto o botão grande do início está na tela.
(function () {
  var alvo = document.getElementById('baixar-hero');
  var raiz = document.documentElement;
  if (!alvo || !('IntersectionObserver' in window)) return;
  new IntersectionObserver(function (es) {
    raiz.classList.toggle('no-topo', es[0].isIntersecting);
  }, { rootMargin: '-60px 0px 0px 0px' }).observe(alvo);
})();
