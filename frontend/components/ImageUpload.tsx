"use client";

import { useCallback, useState, DragEvent } from "react";

interface ImageUploadProps {
    onUpload: (file: File) => void;
    onBeforeUpload?: () => boolean;  // Return false to prevent upload
    hasProfile?: boolean;
}

export default function ImageUpload({ onUpload, onBeforeUpload, hasProfile = true }: ImageUploadProps) {
    const [isDragging, setIsDragging] = useState(false);

    const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);

        // Check if we should proceed
        if (onBeforeUpload && !onBeforeUpload()) {
            return;
        }

        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type.startsWith("image/")) {
            onUpload(files[0]);
        }
    }, [onUpload, onBeforeUpload]);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            onUpload(files[0]);
        }
    }, [onUpload]);

    const handleClick = useCallback(() => {
        // Check if user has profile first
        if (onBeforeUpload && !onBeforeUpload()) {
            return;  // Don't open file picker
        }
        document.getElementById("file-input")?.click();
    }, [onBeforeUpload]);

    return (
        <div className="text-center">
            <h2 className="text-2xl md:text-3xl font-bold mb-4">
                Analyze Your Meal
            </h2>
            <p className="text-zinc-400 mb-8 max-w-lg mx-auto">
                Upload a photo of your food and our AI will identify each item,
                estimate portions, and provide detailed nutritional analysis.
            </p>

            <div
                className={`upload-zone p-12 md:p-16 ${isDragging ? "dragging" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={handleClick}
            >
                <input
                    id="file-input"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleFileSelect}
                />

                <div className="animate-float">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 border border-emerald-500/30 flex items-center justify-center">
                        <svg
                            className="w-10 h-10 text-emerald-400"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                            />
                        </svg>
                    </div>
                </div>

                <p className="text-lg font-medium mb-2">
                    {isDragging ? "Drop your image here" : "Drag & drop your meal photo"}
                </p>
                <p className="text-sm text-zinc-500 mb-6">
                    or click to browse files
                </p>

                <div className="flex flex-wrap justify-center gap-2 text-xs text-zinc-500">
                    <span className="px-3 py-1 rounded-full bg-white/5">JPG</span>
                    <span className="px-3 py-1 rounded-full bg-white/5">PNG</span>
                    <span className="px-3 py-1 rounded-full bg-white/5">WEBP</span>
                    <span className="px-3 py-1 rounded-full bg-white/5">HEIC</span>
                </div>
            </div>

            {/* Demo hint */}
            <p className="mt-8 text-sm text-zinc-500">
                📸 For best results, ensure good lighting and capture the entire plate
            </p>
        </div>
    );
}
