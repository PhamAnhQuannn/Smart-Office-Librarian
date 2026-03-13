export interface SourceCitation {
	file_path: string;
	source_url: string | null;
	start_line: number;
	end_line: number;
	text: string;
}

export function truncateSnippet(text: string, maxLength = 500): string {
	if (text.length <= maxLength) {
		return text;
	}

	return `${text.slice(0, maxLength - 3)}...`;
}

export function sourceFileName(filePath: string): string {
	const parts = filePath.split("/");
	return parts[parts.length - 1] || filePath;
}
