document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const clearFileBtn = document.getElementById('clear-file');
    const summarizeBtn = document.getElementById('summarize-btn');
    const abstractiveBtn = document.getElementById('abstractive');
    const extractiveBtn = document.getElementById('extractive');
    const languageSelect = document.getElementById('language');
    const customPrompt = document.getElementById('custom-prompt');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.querySelector('.progress-fill');
    const resultsSection = document.getElementById('results');
    const summaryContent = document.getElementById('summary-content');
    const processingTime = document.getElementById('processing-time');
    const downloadBtn = document.getElementById('download-btn');
    const copySummaryBtn = document.getElementById('copy-summary');
   


    
    // Application State
    let currentFile = null;
    let currentResult = null;
    
    // Initialize Event Listeners
    function initEventListeners() {
        // File selection
        fileInput.addEventListener('change', handleFileSelect);
        dropArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        ['dragenter', 'dragover'].forEach(event => {
            dropArea.addEventListener(event, highlightDropArea);
        });
        
        ['dragleave', 'drop'].forEach(event => {
            dropArea.addEventListener(event, unhighlightDropArea);
        });
        
        dropArea.addEventListener('drop', handleFileDrop);
        
        // Clear file
        clearFileBtn.addEventListener('click', clearFile);
        
        // Summary type toggle
        abstractiveBtn.addEventListener('click', () => toggleSummaryType('abstractive'));
        extractiveBtn.addEventListener('click', () => toggleSummaryType('extractive'));
        
        // Generate summary
        summarizeBtn.addEventListener('click', generateSummary);
        
        // Copy and download
        copySummaryBtn.addEventListener('click', copySummaryToClipboard);
        downloadBtn.addEventListener('click', downloadPDF);
    }
    
    // File Handling
    function handleFileSelect(e) {
        const files = e.target.files;
        if (files && files.length > 0) {
            processFile(files[0]);
        }
    }
    
    function handleFileDrop(e) {
        e.preventDefault();
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            processFile(files[0]);
        }
    }
    
    function processFile(file) {
        if (file.type === 'application/pdf') {
            currentFile = file;
            fileName.textContent = file.name;
            fileInfo.classList.remove('hidden');
            
            // ✅ Clear past summary before enabling button
            clearResults();
            summaryContent.innerHTML = ''; // Clear old summary from UI
    
            summarizeBtn.disabled = false;
        } else {
            showError('Please upload a PDF file');
        }
    }
    
    function clearFile() {
        fileInput.value = '';
        currentFile = null;
        fileInfo.classList.add('hidden');
        summarizeBtn.disabled = true;
        clearResults();
    }
    
    function highlightDropArea(e) {
        e.preventDefault();
        dropArea.classList.add('highlight');
    }
    
    function unhighlightDropArea(e) {
        e.preventDefault();
        dropArea.classList.remove('highlight');
    }
    
    // Summary Generation
    function toggleSummaryType(type) {
        abstractiveBtn.classList.toggle('active', type === 'abstractive');
        extractiveBtn.classList.toggle('active', type === 'extractive');
        clearResults();
    }
    
    function clearResults() {
        resultsSection.classList.add('hidden');
        summaryContent.innerHTML = '';  // ✅ Clear the summary HTML
        processingTime.textContent = ''; // ✅ Clear processing time too
        currentResult = null;
    }
    
    async function generateSummary() {
        if (!currentFile) return;
    
        // Show loading state
        progressContainer.style.display = 'block';
        progressFill.style.width = '0%';
        setTimeout(() => {
            progressFill.style.width = '100%';
        }, 10);
    
        clearResults();
    
        try {
            const formData = new FormData();
            formData.append("file", currentFile);  // <-- FIXED HERE
            formData.append("summary_length", document.getElementById("summary_length").value);
            formData.append('abstractive', abstractiveBtn.classList.contains('active'));
            formData.append('language', languageSelect.value);
    
            const response = await fetch('/summarize', {
                method: 'POST',
                body: formData
            });
    
            const data = await response.json();
    
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to generate summary');
            }
    
            // Display results
            currentResult = data;
            summaryContent.innerHTML = formatSummary(data.summary);
            processingTime.textContent = `Processed in ${data.processing_time}`;
            resultsSection.classList.remove('hidden');
    
        } catch (error) {
            showError(error.message);
        } finally {
            progressContainer.style.display = 'none';
        }
    }
    
    
    function formatSummary(text) {
        // Convert markdown-like formatting to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/• (.*?)(<br>|$)/g, '<li>$1</li>');
    }
    
    // Output Handling
    function copySummaryToClipboard() {
        if (!currentResult) return;
        
        const textToCopy = summaryContent.textContent;
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                const originalHTML = copySummaryBtn.innerHTML;
                copySummaryBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => {
                    copySummaryBtn.innerHTML = originalHTML;
                }, 2000);
            })
            .catch(err => {
                console.error('Failed to copy:', err);
                showError('Failed to copy text to clipboard');
            });
    }
    
    function downloadPDF() {
        if (!currentResult?.pdf_bytes) return;
        
        try {
            // Decode base64 to binary
            const binaryString = atob(currentResult.pdf_bytes);
            const byteArray = new Uint8Array(binaryString.length);
            
            for (let i = 0; i < binaryString.length; i++) {
                byteArray[i] = binaryString.charCodeAt(i);
            }
            
            // Create Blob and download
            const blob = new Blob([byteArray], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = 'summary.pdf';
            document.body.appendChild(link);
            link.click();
            
            // Clean up
            setTimeout(() => {
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }, 100);
            
        } catch (error) {
            console.error('PDF download failed:', error);
            showError('Failed to download PDF. Please try again.');
        }
    }
    
    // Utility Functions
    function showError(message) {
        alert(`Error: ${message}`);
    }
    
    // Initialize the application
    initEventListeners();
});