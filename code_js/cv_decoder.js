(function() {
    const currentScript = document.currentScript;
    const fileName = currentScript.getAttribute('data-file');
    const targetId = currentScript.getAttribute('data-target'); 
    const filePath = `../text/${fileName}`;
    const element = document.getElementById(targetId);
  
    if (!element) return;
  
    fetch(filePath)
      .then(res => {
        if (!res.ok) throw new Error('File not found: ' + filePath);
        return res.text();
      })
      .then(text => {
        text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  
        text = text
          .replace(/^### (.*$)/gim, '<h3>$1</h3>')
          .replace(/^## (.*$)/gim, '<h2>$1</h2>')
          .replace(/^# (.*$)/gim, '<h1>$1</h1>')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/^-{3,}$/gim, '<hr>')
          .replace(/\n/g, '<br>');
  
        element.innerHTML = text;
      })
      .catch(err => {
        element.textContent = 'Failed to load text.';
        console.error(err);
      });
  })();
  