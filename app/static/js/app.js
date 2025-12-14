/**
 * ObsidianConscierge フロントエンドアプリケーション
 */

// 設定
const CONFIG = {
    API_BASE_URL: '/api/v1',
    DEBOUNCE_MS: 300,
    DEFAULT_LIMIT: 20,
};

// 状態管理
let currentPage = 1;
let currentQuery = '';
let currentTags = '';
let currentLimit = CONFIG.DEFAULT_LIMIT;
let totalResults = 0;
let debounceTimer = null;

// DOM要素
const searchForm = document.getElementById('search-form');
const searchQuery = document.getElementById('search-query');
const tagsFilter = document.getElementById('tags-filter');
const limitSelect = document.getElementById('limit');
const searchButton = document.getElementById('search-button');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const resultsSection = document.getElementById('results-section');
const resultsList = document.getElementById('results-list');
const resultsTitle = document.getElementById('results-title');
const resultsCount = document.getElementById('results-count');
const pagination = document.getElementById('pagination');
const emptyState = document.getElementById('empty-state');

// Obsidian Vault名（設定から取得）
let OBSIDIAN_VAULT_NAME = 'MyVault'; // デフォルト値

/**
 * 設定を読み込む
 */
async function loadConfig() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/config`);
        if (response.ok) {
            const config = await response.json();
            OBSIDIAN_VAULT_NAME = config.obsidian_vault_name || OBSIDIAN_VAULT_NAME;
        }
    } catch (err) {
        console.warn('設定の読み込みに失敗しました:', err);
    }
}

// ページ読み込み時に設定を読み込む
loadConfig();

/**
 * デバウンス関数
 */
function debounce(func, wait) {
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(debounceTimer);
            func(...args);
        };
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(later, wait);
    };
}

/**
 * エラーを表示
 */
function showError(message) {
    error.textContent = message;
    error.classList.remove('hidden');
    loading.classList.add('hidden');
    resultsSection.classList.add('hidden');
    emptyState.classList.add('hidden');
}

/**
 * エラーを非表示
 */
function hideError() {
    error.classList.add('hidden');
}

/**
 * ローディングを表示
 */
function showLoading() {
    loading.classList.remove('hidden');
    error.classList.add('hidden');
    resultsSection.classList.add('hidden');
    emptyState.classList.add('hidden');
}

/**
 * ローディングを非表示
 */
function hideLoading() {
    loading.classList.add('hidden');
}

/**
 * 検索APIを呼び出す
 */
async function search(query, tags = null, limit = CONFIG.DEFAULT_LIMIT, offset = 0) {
    const params = new URLSearchParams({
        q: query,
        limit: limit.toString(),
        offset: offset.toString(),
    });

    if (tags && tags.trim()) {
        params.append('tags', tags);
    }

    const response = await fetch(`${CONFIG.API_BASE_URL}/search?${params.toString()}`);
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '検索に失敗しました' }));
        throw new Error(errorData.detail || '検索に失敗しました');
    }

    return await response.json();
}

/**
 * Obsidianで開くURIを生成
 */
function generateObsidianUri(filePath) {
    // ファイルパスをURLエンコード
    const encodedPath = encodeURIComponent(filePath);
    return `obsidian://open?vault=${encodeURIComponent(OBSIDIAN_VAULT_NAME)}&file=${encodedPath}`;
}

/**
 * 検索結果を表示
 */
function renderResults(data) {
    if (!data.results || data.results.length === 0) {
        resultsList.innerHTML = '<p class="empty-state">検索結果が見つかりませんでした。</p>';
        resultsSection.classList.remove('hidden');
        emptyState.classList.add('hidden');
        return;
    }

    resultsList.innerHTML = data.results.map(result => {
        const similarityPercent = (result.similarity * 100).toFixed(1);
        const tagsHtml = result.tags && result.tags.length > 0
            ? `<div class="result-tags">${result.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>`
            : '';
        
        const obsidianUri = generateObsidianUri(result.file_path);
        const modifiedDate = result.modified ? new Date(result.modified).toLocaleDateString('ja-JP') : '';

        return `
            <div class="result-item">
                <div class="result-header">
                    <h3 class="result-title">${escapeHtml(result.title)}</h3>
                    <span class="result-similarity">類似度: ${similarityPercent}%</span>
                </div>
                <p class="result-summary">${escapeHtml(result.summary || '')}</p>
                <div class="result-meta">
                    ${tagsHtml}
                    ${modifiedDate ? `<span>更新: ${modifiedDate}</span>` : ''}
                    <span>ファイル: ${escapeHtml(result.file_path)}</span>
                </div>
                <div class="result-actions">
                    <a href="${obsidianUri}" class="btn btn-primary">Obsidianで開く</a>
                    <button class="btn btn-secondary" onclick="copyToClipboard('${escapeHtml(result.file_path)}')">パスをコピー</button>
                </div>
            </div>
        `;
    }).join('');

    // 結果情報を更新
    totalResults = data.total;
    resultsCount.textContent = `全 ${totalResults} 件中 ${data.results.length} 件を表示`;
    
    // ページネーションを表示
    renderPagination(data);
    
    resultsSection.classList.remove('hidden');
    emptyState.classList.add('hidden');
}

/**
 * ページネーションを表示
 */
function renderPagination(data) {
    const totalPages = Math.ceil(data.total / data.limit);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    const currentPageNum = data.page;
    const prevDisabled = currentPageNum <= 1;
    const nextDisabled = currentPageNum >= totalPages;

    pagination.innerHTML = `
        <button ${prevDisabled ? 'disabled' : ''} onclick="goToPage(${currentPageNum - 1})">前へ</button>
        <span class="page-info">ページ ${currentPageNum} / ${totalPages}</span>
        <button ${nextDisabled ? 'disabled' : ''} onclick="goToPage(${currentPageNum + 1})">次へ</button>
    `;
}

/**
 * ページ移動
 */
function goToPage(page) {
    currentPage = page;
    performSearch();
}

/**
 * HTMLエスケープ
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * クリップボードにコピー
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // 簡単なフィードバック（オプション）
        alert('パスをクリップボードにコピーしました: ' + text);
    }).catch(err => {
        console.error('コピーに失敗しました:', err);
    });
}

/**
 * 検索を実行
 */
async function performSearch() {
    const query = searchQuery.value.trim();
    
    if (!query) {
        emptyState.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        error.classList.add('hidden');
        loading.classList.add('hidden');
        return;
    }

    currentQuery = query;
    currentTags = tagsFilter.value.trim();
    currentLimit = parseInt(limitSelect.value, 10);
    const offset = (currentPage - 1) * currentLimit;

    showLoading();
    hideError();

    try {
        const data = await search(currentQuery, currentTags, currentLimit, offset);
        hideLoading();
        renderResults(data);
    } catch (err) {
        hideLoading();
        showError(err.message || '検索中にエラーが発生しました');
    }
}

/**
 * リアルタイム検索（デバウンス付き）
 */
const debouncedSearch = debounce(() => {
    currentPage = 1; // 新しい検索時はページをリセット
    performSearch();
}, CONFIG.DEBOUNCE_MS);

/**
 * イベントリスナー
 */
searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    currentPage = 1;
    performSearch();
});

// リアルタイム検索（入力中）
searchQuery.addEventListener('input', () => {
    debouncedSearch();
});

// タグフィルタ変更時
tagsFilter.addEventListener('change', () => {
    currentPage = 1;
    performSearch();
});

// 表示件数変更時
limitSelect.addEventListener('change', () => {
    currentPage = 1;
    performSearch();
});

// 初期状態
emptyState.classList.remove('hidden');

