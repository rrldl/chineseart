document.addEventListener('DOMContentLoaded', () => {
    // 状态管理
    const state = {
        currentTab: 'qa',
        currentImage: null,
        processing: false
    };

    // DOM 元素
    const elements = {
        // 标签页
        tabs: document.querySelectorAll('.tab-btn'),
        panelQa: document.getElementById('panel-qa'),
        panelImageUpload: document.getElementById('panel-image-upload'),
        panelImageSearch: document.getElementById('panel-image-search'),
        panelTextSearch: document.getElementById('panel-text-search'),

        // 艺术问答
        questionInput: document.getElementById('question-input'),
        multiHopCheckbox: document.getElementById('multi-hop'),
        searchDepthSelect: document.getElementById('search-depth'),
        askBtn: document.getElementById('ask-btn'),

        // 图像分析
        imageUpload1: document.getElementById('image-upload-1'),
        preview1: document.getElementById('image-preview-1'),
        previewImg1: document.getElementById('preview-img-1'),
        analyzeBtn: document.getElementById('analyze-btn'),
        uploadArea1: document.getElementById('upload-area-1'),
        uploadZone1: document.querySelector('#upload-area-1 .upload-zone'),

        // 以图搜图
        imageUpload2: document.getElementById('image-upload-2'),
        preview2: document.getElementById('image-preview-2'),
        previewImg2: document.getElementById('preview-img-2'),
        searchImageBtn: document.getElementById('search-image-btn'),
        uploadArea2: document.getElementById('upload-area-2'),
        uploadZone2: document.querySelector('#upload-area-2 .upload-zone'),

        // 以文搜图
        textSearchInput: document.getElementById('text-search-input'),
        searchCountSelect: document.getElementById('search-count'),
        searchTextBtn: document.getElementById('search-text-btn'),

        // 结果区域
        chatHistory: document.getElementById('chat-history'),

        // 状态栏
        statusText: document.getElementById('status-text'),
        processingIndicator: document.getElementById('processing-indicator'),
        processingText: document.getElementById('processing-text'),

        // 模态框
        modal: document.getElementById('search-results-modal'),
        modalTitle: document.getElementById('modal-title'),
        modalBody: document.getElementById('search-results-body'),
        closeModalBtns: document.querySelectorAll('.close-modal')
    };

    // 初始化
    function init() {
        setupEventListeners();
        createImageSearchCountSelector(); // 为以图搜图创建数量选择器
        updateStatus('系统就绪');
    }

    // 为以图搜图创建数量选择器
    function createImageSearchCountSelector() {
        const imageSearchPanel = document.getElementById('panel-image-search');
        if (imageSearchPanel) {
            // 检查是否已经存在数量选择器
            if (imageSearchPanel.querySelector('.search-options')) {
                return;
            }

            // 创建数量选择器HTML
            const countSelectorHtml = `
                <div class="search-options" style="margin: 15px 0; padding: 10px; background: rgba(139, 107, 64, 0.05); border-radius: 8px;">
                    <label style="font-weight: 500; color: #8B6B40; display: block; margin-bottom: 8px;">返回数量：</label>
                    <div class="count-buttons" style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button type="button" class="count-btn active" data-count="1"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: #8B6B40; color: white; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            1个
                        </button>
                        <button type="button" class="count-btn" data-count="2"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            2个
                        </button>
                        <button type="button" class="count-btn" data-count="3"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            3个
                        </button>
                        <button type="button" class="count-btn" data-count="5"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            5个
                        </button>
                        <button type="button" class="count-btn" data-count="10"
                                style="padding: 6px 12px; border: 1px solid #8B6B40; background: white; color: #8B6B40; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.2s;">
                            10个
                        </button>
                    </div>
                </div>
            `;

            // 插入到图片预览和搜索按钮之间
            const previewContainer = imageSearchPanel.querySelector('#image-preview-2');
            const searchButton = imageSearchPanel.querySelector('#search-image-btn');

            if (previewContainer && searchButton) {
                previewContainer.insertAdjacentHTML('afterend', countSelectorHtml);
            } else if (searchButton) {
                searchButton.insertAdjacentHTML('beforebegin', countSelectorHtml);
            }

            // 为数量按钮添加事件
            setTimeout(() => {
                const countButtons = imageSearchPanel.querySelectorAll('.count-btn');
                countButtons.forEach(btn => {
                    btn.addEventListener('click', function() {
                        // 移除所有active类
                        countButtons.forEach(b => {
                            b.classList.remove('active');
                            b.style.background = 'white';
                            b.style.color = '#8B6B40';
                        });

                        // 添加active类到当前按钮
                        this.classList.add('active');
                        this.style.background = '#8B6B40';
                        this.style.color = 'white';

                        // 更新文件信息提示
                        const count = parseInt(this.dataset.count);
                        const fileInfo = imageSearchPanel.querySelector('.file-info');
                        if (fileInfo) {
                            fileInfo.textContent = `查找最相似的${count}个艺术作品`;
                        }

                        updateStatus(`将以图搜图返回 ${count} 个结果`);
                    });
                });
            }, 100);
        }
    }

    // 获取以图搜图选择的数量
    function getImageSearchCount() {
        const selectElement = document.getElementById('image-search-count');
        return selectElement ? parseInt(selectElement.value) : 1;
    }

    // 设置事件监听器
    function setupEventListeners() {
        // 标签页切换
        elements.tabs.forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });

        // 艺术问答
        elements.askBtn.addEventListener('click', handleAskQuestion);
        elements.questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleAskQuestion();
            }
        });

        // 图像分析
        setupImageUpload(elements.imageUpload1, elements.preview1, elements.previewImg1, 'analyze');
        elements.analyzeBtn.addEventListener('click', handleImageAnalysis);
        setupDragAndDrop(elements.uploadArea1, elements.imageUpload1);

        // 修复点击上传区域触发文件选择
        if (elements.uploadZone1) {
            elements.uploadZone1.addEventListener('click', (e) => {
                if (!e.target.matches('input')) {
                    elements.imageUpload1.click();
                }
            });
        }

        // 以图搜图
        setupImageUpload(elements.imageUpload2, elements.preview2, elements.previewImg2, 'search');
        elements.searchImageBtn.addEventListener('click', handleImageSearch);
        setupDragAndDrop(elements.uploadArea2, elements.imageUpload2);

        // 修复点击上传区域触发文件选择
        if (elements.uploadZone2) {
            elements.uploadZone2.addEventListener('click', (e) => {
                if (!e.target.matches('input')) {
                    elements.imageUpload2.click();
                }
            });
        }

        // 以文搜图
        elements.searchTextBtn.addEventListener('click', handleTextSearch);
        elements.textSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleTextSearch();
            }
        });

        // 移除图片按钮
        document.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.closest('.remove-btn').dataset.id;
                removeImage(id);
            });
        });

        // 模态框关闭
        elements.closeModalBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                elements.modal.classList.add('hidden');
            });
        });

        // 点击模态框外部关闭
        elements.modal.addEventListener('click', (e) => {
            if (e.target === elements.modal) {
                elements.modal.classList.add('hidden');
            }
        });
    }

    // 标签页切换
    function switchTab(tabId) {
        state.currentTab = tabId;

        // 更新标签按钮
        elements.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });

        // 更新内容面板
        elements.panelQa.classList.toggle('active', tabId === 'qa');
        elements.panelImageUpload.classList.toggle('active', tabId === 'image-upload');
        elements.panelImageSearch.classList.toggle('active', tabId === 'image-search');
        elements.panelTextSearch.classList.toggle('active', tabId === 'text-search');

        // 清空预览
        removeImage('1');
        removeImage('2');

        updateStatus('选择功能模式: ' + getTabName(tabId));
    }

    function getTabName(tabId) {
        const names = {
            'qa': '艺术问答',
            'image-upload': '图像分析',
            'image-search': '以图搜图',
            'text-search': '以文搜图'
        };
        return names[tabId] || '未知模式';
    }

    // 设置图片上传
    function setupImageUpload(inputElement, previewElement, previewImgElement, type) {
        inputElement.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                if (!validateImageFile(file)) {
                    return;
                }
                displayImagePreview(file, previewElement, previewImgElement);
                updateButtonState(type);
            }
        });

        // 确保文件输入框样式正确
        inputElement.style.position = 'absolute';
        inputElement.style.width = '100%';
        inputElement.style.height = '100%';
        inputElement.style.opacity = '0';
        inputElement.style.cursor = 'pointer';
        inputElement.style.zIndex = '10';
        inputElement.style.top = '0';
        inputElement.style.left = '0';
    }

    // 设置拖拽上传
    function setupDragAndDrop(dropZone, inputElement) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = 'rgba(139, 107, 64, 0.1)';
                dropZone.style.borderColor = '#8B6B40';
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = '';
                dropZone.style.borderColor = '';
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                if (!validateImageFile(file)) {
                    return;
                }
                inputElement.files = e.dataTransfer.files;
                const previewId = inputElement.id === 'image-upload-1' ? '1' : '2';
                const previewElement = document.getElementById(`image-preview-${previewId}`);
                const previewImgElement = document.getElementById(`preview-img-${previewId}`);
                displayImagePreview(file, previewElement, previewImgElement);
                updateButtonState(previewId === '1' ? 'analyze' : 'search');
            }
        }, false);
    }

    // 验证图片文件
    function validateImageFile(file) {
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff'];

        if (!allowedTypes.includes(file.type)) {
            alert('不支持的文件类型。请上传PNG、JPG、JPEG、GIF、BMP或TIFF格式的图片。');
            return false;
        }

        if (file.size > 10 * 1024 * 1024) {
            alert('图片大小不能超过10MB');
            return false;
        }

        return true;
    }

    // 显示图片预览
    function displayImagePreview(file, previewElement, previewImgElement) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImgElement.src = e.target.result;
            previewElement.classList.remove('hidden');
            updateStatus(`已选择图片: ${file.name} (${(file.size / 1024).toFixed(1)}KB)`);
        };
        reader.readAsDataURL(file);
    }

    // 移除图片
    function removeImage(id) {
        const input = document.getElementById(`image-upload-${id}`);
        const preview = document.getElementById(`image-preview-${id}`);

        if (input) {
            input.value = '';
            // 重置文件输入
            const newInput = input.cloneNode(true);
            input.parentNode.replaceChild(newInput, input);

            // 重新设置事件监听器
            if (id === '1') {
                elements.imageUpload1 = newInput;
                setupImageUpload(elements.imageUpload1, elements.preview1, elements.previewImg1, 'analyze');
            } else {
                elements.imageUpload2 = newInput;
                setupImageUpload(elements.imageUpload2, elements.preview2, elements.previewImg2, 'search');
            }
        }
        if (preview) preview.classList.add('hidden');

        updateButtonState(id === '1' ? 'analyze' : 'search');
        updateStatus('系统就绪');
    }

    // 更新按钮状态
    function updateButtonState(type) {
        if (type === 'analyze') {
            const hasImage = !elements.preview1.classList.contains('hidden');
            elements.analyzeBtn.disabled = !hasImage;
            elements.analyzeBtn.style.opacity = hasImage ? '1' : '0.5';
            elements.analyzeBtn.style.cursor = hasImage ? 'pointer' : 'not-allowed';
        } else if (type === 'search') {
            const hasImage = !elements.preview2.classList.contains('hidden');
            elements.searchImageBtn.disabled = !hasImage;
            elements.searchImageBtn.style.opacity = hasImage ? '1' : '0.5';
            elements.searchImageBtn.style.cursor = hasImage ? 'pointer' : 'not-allowed';
        }
    }

    // 更新状态
    function updateStatus(text) {
        elements.statusText.textContent = text;
    }

    // 显示处理状态
    function showProcessing(text) {
        state.processing = true;
        elements.processingText.textContent = text;
        elements.processingIndicator.classList.remove('hidden');
        updateStatus(text);
    }

    // 隐藏处理状态
    function hideProcessing() {
        state.processing = false;
        elements.processingIndicator.classList.add('hidden');
        updateStatus('系统就绪');
    }

    // 添加消息到聊天历史
    function addMessage(content, type = 'assistant', timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        if (!timestamp) {
            timestamp = new Date().toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        const header = type === 'user' ?
            '<i class="fas fa-user"></i> 您' :
            '<i class="fas fa-robot"></i> 墨韵灵境';

        messageDiv.innerHTML = `
            <div class="message-header">${header}</div>
            <div class="message-content">${content}</div>
            <div class="message-time">${timestamp}</div>
        `;

        elements.chatHistory.appendChild(messageDiv);
        messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });

        return messageDiv;
    }

    // 处理艺术问答
    async function handleAskQuestion() {
        const question = elements.questionInput.value.trim();
        if (!question) {
            alert('请输入问题');
            return;
        }

        // 添加用户消息
        addMessage(question, 'user');
        elements.questionInput.value = '';

        // 显示处理状态
        showProcessing('正在思考...');

        try {
            // 准备请求数据
            const requestData = {
                question: question,
                enable_multi_hop: elements.multiHopCheckbox.checked,
                search_budget: elements.searchDepthSelect.value
            };

            // 发送请求
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // 处理SSE流
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let answer = '';
            let thinkingProcess = '';

            // 添加一个临时消息显示思考过程
            const thinkingMessage = addMessage('正在分析问题...', 'assistant');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.type === 'log_html') {
                                // 处理思考过程（可以记录但不显示）
                                thinkingProcess += data.content + '\n';
                            } else if (data.type === 'answer') {
                                answer = data.content;
                            }
                        } catch (e) {
                            console.error('解析SSE数据失败:', e);
                        }
                    }
                }
            }

            // 更新消息内容
            thinkingMessage.querySelector('.message-content').innerHTML = answer || '未能获取到答案';

        } catch (error) {
            console.error('问答请求失败:', error);
            addMessage(`抱歉，处理问题时出现错误: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
        }
    }

    // 处理图像分析（分割和描述）
    async function handleImageAnalysis() {
        const fileInput = elements.imageUpload1;
        if (!fileInput.files[0]) {
            alert('请先选择图片');
            return;
        }

        // 显示处理状态
        showProcessing('正在上传和分析图片...');

        try {
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);

            // 添加用户消息（显示图片）
            const userMessage = addMessage('上传图片进行分析...', 'user');

            // 在消息中添加图片预览
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.style.maxWidth = '200px';
                img.style.borderRadius = '8px';
                img.style.marginTop = '10px';
                userMessage.querySelector('.message-content').appendChild(img);
            };
            reader.readAsDataURL(fileInput.files[0]);

            // 发送请求
            const response = await fetch('/upload_image', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                // 显示分割和描述结果
                const content = `
                    <div class="segmentation-result">
                        <h4>图像分析结果</h4>
                        <div class="result-images">
                            <div class="result-image">
                                <img src="${result.original_image}" alt="原始图片">
                                <div class="result-caption">原始图片</div>
                            </div>
                            <div class="result-image">
                                <img src="${result.segmented_image}" alt="分割结果">
                                <div class="result-caption">分割结果</div>
                            </div>
                        </div>
                        <div class="description-box">
                            <h4>图像描述</h4>
                            <p>${result.description || '未能生成描述'}</p>
                        </div>
                    </div>
                `;

                addMessage(content, 'assistant');
            } else {
                throw new Error(result.error || '图像处理失败');
            }

        } catch (error) {
            console.error('图像分析失败:', error);
            addMessage(`图像分析失败: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
            removeImage('1');
        }
    }

    // 处理以图搜图
    async function handleImageSearch() {
        const fileInput = elements.imageUpload2;
        if (!fileInput.files[0]) {
            alert('请先选择图片');
            return;
        }

        // 获取选择的数量
        const count = getImageSearchCount();

        // 显示处理状态
        showProcessing(`正在搜索 ${count} 个相似作品...`);

        try {
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);
            formData.append('count', count);  // 添加数量参数

            // 添加用户消息
            const userMessage = addMessage(`搜索相似艺术作品 (请求 ${count} 个)...`, 'user');

            // 在消息中添加图片预览
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.style.maxWidth = '150px';
                img.style.borderRadius = '8px';
                img.style.marginTop = '10px';
                userMessage.querySelector('.message-content').appendChild(img);
            };
            reader.readAsDataURL(fileInput.files[0]);

            // 发送请求
            const response = await fetch('/search_by_image', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                const artworks = result.results || [];

                // 显示搜索结果摘要
                const summary = result.message || `找到 ${artworks.length} 个相似作品 (请求 ${count} 个)`;
                const assistantMessage = addMessage(summary + '<br><button class="view-details-btn" style="margin-top:10px;">查看详情</button>', 'assistant');

                // 为查看详情按钮添加事件
                assistantMessage.querySelector('.view-details-btn').addEventListener('click', () => {
                    showSearchResults(artworks, '图片搜索结果');
                });

                // 保存结果以便在模态框中显示
                window.currentSearchResults = artworks;

            } else {
                throw new Error(result.error || '未找到相似作品');
            }

        } catch (error) {
            console.error('以图搜图失败:', error);
            addMessage(`搜索失败: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
            removeImage('2');
        }
    }

    // 处理以文搜图
    async function handleTextSearch() {
        const text = elements.textSearchInput.value.trim();
        if (!text) {
            alert('请输入搜索描述');
            return;
        }

        // 获取选择的数量
        const count = parseInt(elements.searchCountSelect.value);

        // 添加用户消息
        addMessage(`搜索: "${text}" (请求 ${count} 个结果)`, 'user');
        elements.textSearchInput.value = '';

        // 显示处理状态
        showProcessing(`正在搜索 ${count} 个相关作品...`);

        try {
            // 准备请求数据
            const requestData = {
                text: text,
                count: count  // 添加数量参数
            };

            // 发送请求
            const response = await fetch('/search_by_text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (result.success) {
                const artworks = result.results || [];

                // 显示搜索结果摘要
                const summary = result.message || `找到 ${artworks.length} 个相关作品 (请求 ${count} 个)`;
                const assistantMessage = addMessage(summary + '<br><button class="view-details-btn" style="margin-top:10px;">查看详情</button>', 'assistant');

                // 为查看详情按钮添加事件
                assistantMessage.querySelector('.view-details-btn').addEventListener('click', () => {
                    showSearchResults(artworks, '文字搜索结果');
                });

                // 保存结果
                window.currentSearchResults = artworks;

            } else {
                throw new Error(result.error || '未找到相关作品');
            }

        } catch (error) {
            console.error('以文搜图失败:', error);
            addMessage(`搜索失败: ${error.message}`, 'assistant');
        } finally {
            hideProcessing();
        }
    }

    // 显示搜索结果模态框
    function showSearchResults(artworks, title) {
        elements.modalTitle.textContent = title;

        if (!artworks || artworks.length === 0) {
            elements.modalBody.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">未找到相关作品</div>';
        } else {
            // 按相似度排序
            const sortedArtworks = [...artworks].sort((a, b) => {
                const simA = a.similarity || 0;
                const simB = b.similarity || 0;
                return simB - simA; // 降序排列，相似度高的在前
            });

            let html = `<div class="search-result-grid">`;

            sortedArtworks.forEach((artwork, index) => {
                // 使用完整的作品信息
                const title = artwork.title || artwork.properties?.title || '未命名作品';
                const author = artwork.author || artwork.properties?.author || artwork.properties?.created_by || '未知作者';
                const dynasty = artwork.dynasty || artwork.properties?.dynasty || '';
                const similarity = artwork.similarity !== undefined ? 
                                 `相似度: ${artwork.similarity.toFixed(1)}%` : '';
                // 构造图片URL - 直接使用画作标题
                let imageUrl = '';
                if (title && title !== '未命名作品') {
                    // 直接使用画作标题作为文件名（前端会编码特殊字符）
                    const encodedTitle = encodeURIComponent(title);
                    imageUrl = `/artwork_image/${encodedTitle}`;
                }

                html += `
                    <div class="artwork-card" data-index="${index}">
                        <div class="artwork-image-container">
                            ${imageUrl ? 
                                `<img src="${imageUrl}" alt="${title}" class="artwork-image" 
                                     onerror="handleImageError(this, '${title}')">` : 
                                `<div class="artwork-placeholder">无图片</div>`}
                        </div>
                        <div class="artwork-info">
                            <div class="artwork-title" title="${title}">
                                ${title}
                            </div>
                            <div class="artwork-author">${author}</div>
                            ${dynasty ? `<div class="artwork-dynasty">${dynasty}</div>` : ''}
                            ${similarity ? `<div class="artwork-similarity">${similarity}</div>` : ''}
                        </div>
                    </div>
                `;
            });

            html += `</div>`;
            elements.modalBody.innerHTML = html;

            // 为每张卡片添加点击事件
            document.querySelectorAll('.artwork-card').forEach((card, index) => {
                card.addEventListener('click', () => {
                    showArtworkDetail(sortedArtworks[index]);
                });
            });
        }

        elements.modal.classList.remove('hidden');
    }

    // 图片错误处理函数（全局）
    window.handleImageError = function(img, title) {
        console.warn(`图片加载失败: ${title}`);
        
        // 先尝试不同的扩展名
        const extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'];
        const baseName = encodeURIComponent(title);
        
        let currentIndex = 0;
        
        function tryNextExtension() {
            if (currentIndex < extensions.length) {
                const ext = extensions[currentIndex];
                const newSrc = `/artwork_image/${baseName}${ext}`;
                console.log(`尝试图片: ${newSrc}`);
                
                // 创建一个新的Image对象测试
                const testImg = new Image();
                testImg.onload = function() {
                    img.src = newSrc;
                    console.log(`成功加载图片: ${newSrc}`);
                };
                testImg.onerror = function() {
                    currentIndex++;
                    tryNextExtension();
                };
                testImg.src = newSrc;
            } else {
                // 所有扩展名都失败，显示占位符
                img.onerror = null;
                img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150"><rect width="200" height="150" fill="#f0f0f0"/><text x="100" y="75" font-size="14" text-anchor="middle" fill="#999">图片加载失败</text></svg>';
            }
        }
        
        tryNextExtension();
    };

    // 显示画作详情
    async function showArtworkDetail(artwork) {
        const title = artwork.title || artwork.properties?.title || '未知作品';
        const author = artwork.author || artwork.properties?.author || artwork.properties?.created_by || '未知作者';
        const dynasty = artwork.dynasty || artwork.properties?.dynasty || '未知';
        const style = artwork.style || artwork.properties?.style || artwork.medium || '未知';
        const description = artwork.description || artwork.properties?.description || '暂无描述';
        const medium = artwork.medium || artwork.properties?.medium || '';
        const dimensions = artwork.dimensions || artwork.properties?.dimensions || '';
        const collection = artwork.collection || artwork.properties?.collection || '';
        const similarity = artwork.similarity !== undefined ? 
                        `相似度: ${artwork.similarity.toFixed(1)}%` : '';

        // 尝试获取更多详细信息
        let moreDetails = '';
        try {
            const response = await fetch(`/get_artwork_details/${encodeURIComponent(title)}`);
            if (response.ok) {
                const detailResult = await response.json();
                if (detailResult && detailResult.a) {
                    // 使用详细数据
                    const detailedArtwork = detailResult.a;
                    const detailedAuthor = detailResult.authors ? detailResult.authors.join(', ') : author;
                    const detailedDynasty = detailResult.dynasties ? detailResult.dynasties.join(', ') : dynasty;
                    
                    // 构建详细描述
                    moreDetails = `
作品详情
============
标题: ${detailedArtwork.title || title}
作者: ${detailedAuthor}
朝代: ${detailedDynasty}
风格: ${detailedArtwork.style || style}
材质: ${detailedArtwork.medium || medium}
尺寸: ${detailedArtwork.dimensions || dimensions}
收藏: ${detailedArtwork.collection || collection}
描述: ${detailedArtwork.description || description}
${similarity}
                    `;
                }
            }
        } catch (e) {
            console.error('获取详细详情失败:', e);
        }

        // 如果没有获取到详细信息，使用基本数据
        if (!moreDetails) {
            moreDetails = `
作品详情
============
标题: ${title}
作者: ${author}
朝代: ${dynasty}
风格: ${style}
${medium ? `材质: ${medium}` : ''}
${dimensions ? `尺寸: ${dimensions}` : ''}
${collection ? `收藏: ${collection}` : ''}
描述: ${description}
${similarity}
            `;
        }

        // 创建一个自定义的模态框来显示详情
        const detailModal = document.createElement('div');
        detailModal.className = 'modal';
        detailModal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        `;

        const detailContent = document.createElement('div');
        detailContent.className = 'modal-content';
        detailContent.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 10px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        `;

        // 添加图片
        let imageHtml = '';
        let imageUrl = '';
        if (artwork.image_url) {
            imageUrl = artwork.image_url;
        } else if (title && title !== '未知作品') {
            const encodedTitle = encodeURIComponent(title);
            imageUrl = `/artwork_image/${encodedTitle}`;
        }
        
        if (imageUrl) {
            imageHtml = `<img src="${imageUrl}" alt="${title}" style="max-width:100%;margin-bottom:20px;border-radius:5px;" onerror="this.style.display='none'">`;
        }

        detailContent.innerHTML = `
            <button class="close-detail" style="position:absolute;top:10px;right:10px;background:none;border:none;font-size:20px;cursor:pointer;">×</button>
            <h3 style="color:#333;margin-bottom:20px;border-bottom:2px solid #8B6B40;padding-bottom:10px;">${title}</h3>
            ${imageHtml}
            <div style="color:#666;line-height:1.6;">
                <p><strong>作者:</strong> ${author}</p>
                <p><strong>朝代:</strong> ${dynasty}</p>
                <p><strong>风格:</strong> ${style}</p>
                ${medium ? `<p><strong>材质:</strong> ${medium}</p>` : ''}
                ${dimensions ? `<p><strong>尺寸:</strong> ${dimensions}</p>` : ''}
                ${collection ? `<p><strong>收藏:</strong> ${collection}</p>` : ''}
                ${similarity ? `<p><strong>${similarity}</strong></p>` : ''}
                <p><strong>描述:</strong> ${description}</p>
            </div>
        `;

        detailModal.appendChild(detailContent);
        document.body.appendChild(detailModal);

        // 添加关闭事件
        detailModal.addEventListener('click', (e) => {
            if (e.target === detailModal || e.target.classList.contains('close-detail')) {
                document.body.removeChild(detailModal);
            }
        });
    }

    // 初始化应用
    init();
});
