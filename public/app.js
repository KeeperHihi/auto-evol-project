(function () {
    const form = document.getElementById('evolveForm');
    const promptInput = document.getElementById('promptInput');
    const iterationsInput = document.getElementById('iterationsInput');
    const submitBtn = document.getElementById('submitBtn');
    const logOutput = document.getElementById('logOutput');

    let running = false;

    function appendLog(message) {
        const text = String(message || '').trim();
        if (!text) {
            return;
        }
        if (logOutput.textContent === '等待任务启动...') {
            logOutput.textContent = '';
        }
        logOutput.textContent += `${text}\n`;
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    function setRunning(next) {
        running = Boolean(next);
        submitBtn.disabled = running;
        submitBtn.textContent = running ? '进化中...' : '开始自进化';
    }

    async function runEvolution(prompt, iterations) {
        setRunning(true);
        appendLog(`[CLIENT] 已发起请求，轮次=${iterations}`);

        try {
            const response = await fetch('/api/evolve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, iterations })
            });

            if (!response.ok) {
                let message = `请求失败: HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData && errorData.error) {
                        message = `${message} - ${errorData.error}`;
                    }
                } catch (parseError) {
                    // ignore
                }
                throw new Error(message);
            }

            if (!response.body) {
                throw new Error('服务端未返回可读流');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';

                for (const eventChunk of events) {
                    const lines = eventChunk.split('\n');
                    for (const rawLine of lines) {
                        const line = rawLine.trim();
                        if (!line.startsWith('data:')) {
                            continue;
                        }
                        const payload = line.slice(5).trim();
                        if (!payload) {
                            continue;
                        }
                        if (payload === '[DONE]') {
                            appendLog('[CLIENT] 流结束。');
                            setRunning(false);
                            return;
                        }

                        try {
                            const parsed = JSON.parse(payload);
                            appendLog(parsed.message || payload);
                            if (parsed.loading === false) {
                                setRunning(false);
                            }
                        } catch (error) {
                            appendLog(payload);
                        }
                    }
                }
            }

            setRunning(false);
        } catch (error) {
            appendLog(`[CLIENT][ERROR] ${error.message}`);
            setRunning(false);
        }
    }

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        if (running) {
            return;
        }

        const prompt = String(promptInput.value || '').trim();
        if (!prompt) {
            appendLog('[CLIENT] 请输入网站方向 prompt。');
            return;
        }

        const iterations = Math.max(1, Math.min(10, Number(iterationsInput.value) || 3));
        runEvolution(prompt, iterations);
    });
})();
