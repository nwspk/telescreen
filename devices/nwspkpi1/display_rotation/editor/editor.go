package main

const editorHTML = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Display Page Editor</title>
    <style>
        body {
            margin: 0;
            font-family: -apple-system, system-ui, BlinkMacSystemFont;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .container {
            display: flex;
            flex: 1;
            padding: 20px;
            gap: 20px;
        }
        .sidebar {
            width: 200px;
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            height: fit-content;
        }
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #333;
            color: white;
            padding: 15px 20px;
        }
        .file-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .file-list li {
            padding: 8px 12px;
            cursor: pointer;
            border-radius: 4px;
        }
        .file-list li:hover {
            background: #e0e0e0;
        }
        .controls {
            margin-bottom: 15px;
        }
        #editor {
            width: 100%;
            height: 400px;
            margin-bottom: 15px;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-family: monospace;
            resize: vertical;
        }
        button {
            background: #007AFF;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 8px;
        }
        button:hover {
            background: #0056b3;
        }
        #filename {
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-right: 8px;
        }
        #preview {
            border: 1px solid #ccc;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0">Display Page Editor</h2>
    </div>
    <div class="container">
        <div class="sidebar">
            <h3>Pages</h3>
            <ul id="fileList" class="file-list"></ul>
        </div>
        <div class="main">
            <div class="controls">
                <input type="text" id="filename" placeholder="filename.html">
                <button onclick="save()">Save</button>
                <button onclick="preview()">Preview</button>
                <button onclick="newFile()">New File</button>
            </div>
            <div id="status" class="status"></div>
            <textarea id="editor" placeholder="Enter your HTML content here"></textarea>
            <div id="preview"></div>
        </div>
    </div>
    <script>
        const newPageTemplate = ` + "`" + newPageTemplate + "`" + `;

	function loadFile(filename) {
	    // Add cache-busting query parameter
	    fetch('/pages/' + filename + '?t=' + new Date().getTime())
	        .then(response => response.text())
	        .then(content => {
	            document.getElementById('editor').value = content;
	            document.getElementById('filename').value = filename;
	        })
	        .catch(error => showStatus('Error loading file', true));
	}

	function loadFileList() {
	    // Add cache-busting query parameter
	    fetch('/api/files' + '?t=' + new Date().getTime())
	        .then(response => response.json())
	        .then(files => {
	            const list = document.getElementById('fileList');
	            list.innerHTML = '';
	            files.forEach(file => {
	                const li = document.createElement('li');
	                li.textContent = file;
	                li.onclick = () => loadFile(file);
	                list.appendChild(li);
	            });
	        })
	        .catch(error => showStatus('Error loading file list', true));
	}

        function newFile() {
            document.getElementById('editor').value = newPageTemplate;
            document.getElementById('filename').value = 'page_' + 
                new Date().toISOString().slice(0,10) + '.html';
            document.getElementById('preview').innerHTML = newPageTemplate;
            showStatus('New template loaded');
        }

        function save() {
            const content = document.getElementById('editor').value;
            const filename = document.getElementById('filename').value;

            if (!filename) {
                showStatus('Please enter a filename', true);
                return;
            }

            if (!filename.endsWith('.html')) {
                showStatus('Filename must end with .html', true);
                return;
            }

            const formData = new FormData();
            formData.append('filename', filename);
            formData.append('content', content);

            fetch('/api/save', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    showStatus('File saved successfully');
                    loadFileList();
                } else {
                    throw new Error('Save failed');
                }
            })
            .catch(error => showStatus('Error saving file', true));
        }

        function preview() {
            const content = document.getElementById('editor').value;
            document.getElementById('preview').innerHTML = content;
        }

        function showStatus(message, isError = false) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + (isError ? 'error' : 'success');
            status.style.display = 'block';
            setTimeout(() => status.style.display = 'none', 3000);
        }

        loadFileList();
    </script>
</body>
</html>`
