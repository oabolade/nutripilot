"use client";

interface StreamingAnalysisProps {
    content: string;
    toolCalls: string[];
}

export default function StreamingAnalysis({ content, toolCalls }: StreamingAnalysisProps) {
    // Parse streaming content for display
    const lines = content.split("\n").filter(Boolean);

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm text-emerald-400 font-medium">AI Analysis in Progress</span>
            </div>

            {/* Tool calls display */}
            {toolCalls.length > 0 && (
                <div className="space-y-2 mb-4">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider">Agent Actions</p>
                    {toolCalls.map((tool, index) => (
                        <div
                            key={index}
                            className="flex items-center gap-2 text-sm text-zinc-400 p-2 rounded-lg bg-white/5"
                        >
                            <span className="text-emerald-400">✓</span>
                            <span>{tool}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Streaming text display */}
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="prose prose-invert prose-sm max-w-none">
                    {content ? (
                        <div className="text-zinc-300 whitespace-pre-wrap font-mono text-sm">
                            {content}
                            <span className="inline-block w-2 h-4 bg-emerald-400 animate-pulse ml-1" />
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 text-zinc-400">
                            <div className="w-4 h-4 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
                            <span>Waiting for AI response...</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Progress indicators */}
            <div className="grid grid-cols-4 gap-2">
                {["Detect", "Lookup", "Analyze", "Score"].map((step, i) => (
                    <div
                        key={step}
                        className={`text-center p-2 rounded-lg border ${i < 2
                                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                                : "bg-white/5 border-white/10 text-zinc-500"
                            }`}
                    >
                        <span className="text-xs">{step}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
