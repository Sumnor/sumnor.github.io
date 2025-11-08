(function() {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
    script.onload = function() {
      pdfjsLib.GlobalWorkerOptions.workerSrc = 
        'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
      loadAndFormatPDF();
    };
    script.onerror = function() {
      document.getElementById('resume-text').innerHTML = 
        '<span style="color: #ff6b6b;">Failed to load PDF library</span>';
    };
    document.head.appendChild(script);
  })();

  async function loadAndFormatPDF() {
    const container = document.getElementById('resume-text');
    const pdfPath = './text/resume.pdf';

    try {
      container.textContent = 'Loading PDF...';
      
      const loadingTask = pdfjsLib.getDocument(pdfPath);
      const pdf = await loadingTask.promise;
      
      let allText = '';

      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        
        let lastY = null;
        let lineText = '';
        
        textContent.items.forEach((item) => {
          const currentY = item.transform[5];
          
          if (lastY !== null && Math.abs(currentY - lastY) > 5) {
            allText += lineText.trim() + '\n';
            lineText = '';
          }
          
          if (lineText && !lineText.endsWith(' ')) {
            lineText += ' ';
          }
          
          lineText += item.str;
          lastY = currentY;
        });
        
        if (lineText.trim()) {
          allText += lineText.trim() + '\n';
        }
      }

      formatResume(allText);
      
    } catch (err) {
      container.innerHTML = 
        '<span style="color: #ff6b6b;">Failed to load PDF</span><br><br>' +
        'Error: ' + err.message + '<br><br>' +
        '<a href="' + pdfPath + '" style="color: #a70303;">Open PDF directly</a>';
    }
  }

  function formatResume(text) {
    const container = document.getElementById('resume-text');
    const lines = text.split('\n').filter(line => line.trim());
    
    let html = '';
    let currentJobTitle = '';
    let collectingBullets = false;
    
    const sectionHeaders = ['PROFESSIONAL SUMMARY', 'WORK EXPERIENCE', 'EDUCATION', 
                            'TECHNICAL SKILLS', 'CERTIFICATIONS', 'PROJECTS', 'SKILLS'];
    
    lines.forEach((line, index) => {
      line = line.trim();
      
      if (index === 0) {
        html += `<div class="resume-name">${line}</div>`;
      }
      else if (index === 1) {
        html += `<div class="resume-title">${line}</div>`;
      }
      else if (line.includes('@') || line.includes('Email:') || line.includes('Phone:') || 
               line.includes('LinkedIn:') || line.includes('GitHub:')) {
        if (!html.includes('class="resume-contact"')) {
          html += '<div class="resume-contact">';
        }
        html += `${line}<br>`;
        if (index + 1 < lines.length) {
          const nextLine = lines[index + 1].trim();
          if (!nextLine.includes('@') && !nextLine.includes('Email:') && 
              !nextLine.includes('Phone:') && !nextLine.includes('LinkedIn:') && 
              !nextLine.includes('GitHub:')) {
            html += '</div>';
          }
        } else {
          html += '</div>';
        }
      }
      else if (sectionHeaders.some(header => line.toUpperCase().includes(header))) {
        html += `<div class="resume-section-title">${line}</div>`;
        collectingBullets = false;
      }
      else if (!line.startsWith('-') && !line.startsWith('•') && 
               line.length < 60 && line.length > 5 &&
               !line.includes('|') && 
               (index + 1 < lines.length && 
                (lines[index + 1].includes('|') || lines[index + 1].includes(',')))) {
        html += `<div class="resume-job-title">${line}</div>`;
        currentJobTitle = line;
      }
      else if (line.includes('|') || 
               (line.match(/\d{4}/) && (line.includes(',') || line.includes('-')))) {
        html += `<div class="resume-company">${line}</div>`;
        collectingBullets = true;
      }
      else if (line.startsWith('-') || line.startsWith('•')) {
        const cleanLine = line.substring(1).trim();
        html += `<div class="resume-text">• ${cleanLine}</div>`;
      }
      else if (line.length > 0) {
        if (collectingBullets && !line.match(/^\d{4}/) && line.length > 10) {
          html += `<div class="resume-text">• ${line}</div>`;
        } else {
          html += `<div class="resume-text">${line}</div>`;
        }
      }
    });
    
    container.innerHTML = html;
  }