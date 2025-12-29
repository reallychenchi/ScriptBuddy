// src/services/deepseek.ts
import { IReviewer } from './interfaces';

export class DeepSeekReviewer implements IReviewer {
    private apiKey: string;
    private baseUrl: string;

    constructor(apiKey: string, baseUrl: string = 'https://api.deepseek.com') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
    }

    async judgeIntent(userText: string, context?: any): Promise<string> {
        // Return NONE if text is too short to be an command
        if (userText.length < 2) return 'NONE';

        const systemPrompt = `
You are an intent classifier for a Script Rehearsal App.
User is rehearsing lines. You need to analyze if their input contains a CONTROL COMMAND.

Possible Intents:
- STOP: User wants to stop/quit/exit. (e.g. "我不练了", "退出", "停止")
- RESTART: User wants to start over. (e.g. "重来", "重新开始")
- CHANGE_ROLE: User wants to switch role. (e.g. "我想演甲", "换个角色")
- CHANGE_LEVEL: User wants to change difficulty/mastery. (e.g. "太难了", "不需要提示了")
- NONE: User is just determining lines or saying something irrelevant to control.

Return ONLY the Intent Enum String.
    `.trim();

        try {
            const response = await fetch(`${this.baseUrl}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.apiKey}`
                },
                body: JSON.stringify({
                    model: "deepseek-chat",
                    messages: [
                        { role: "system", content: systemPrompt },
                        { role: "user", content: `User Input: "${userText}"\nContext: ${JSON.stringify(context || {})}` }
                    ],
                    temperature: 0.1,
                    stream: false
                })
            });

            if (!response.ok) {
                console.error('DeepSeek API Error', await response.text());
                return 'NONE';
            }

            const data = await response.json();
            const content = data.choices[0]?.message?.content?.trim() || 'NONE';

            // Safety check to ensure valid enum
            if (['STOP', 'RESTART', 'CHANGE_ROLE', 'CHANGE_LEVEL', 'NONE'].includes(content)) {
                return content;
            }
            return 'NONE';

        } catch (e) {
            console.error('Intent Check Failed', e);
            return 'NONE';
        }
    }
}
