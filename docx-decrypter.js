(async function() {
    const currentScript = document.currentScript;
    const fileName = currentScript.getAttribute('data-file');
    const targetId = currentScript.getAttribute('data-target');
    const filePath = `text/${fileName}`;
    const element = document.getElementById(targetId);
  
    if (!element) return;
  
    try {
      const loadingTask = pdfjsLib.getDocument(filePath);
      const pdf = await loadingTask.promise;
      let fullText = '';
  
      // Loop through all pages
      for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
        const page = await pdf.getPage(pageNum);
        const content = await page.getTextContent();
        const pageText = content.items.map(item => item.str).join(' ');
        fullText += pageText + '\n\n';
      }
  
      // Insert text into element
      element.innerHTML = fullText.replace(/\n/g, '<br>');
    } catch (err) {
      console.error(err);
      element.textContent = 'Failed to load PDF.';
    }
  })();
  