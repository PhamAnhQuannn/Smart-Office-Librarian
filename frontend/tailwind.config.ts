import type { Config } from "tailwindcss";

const config: Config = {
	content: [
		"./app/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./hooks/**/*.{ts,tsx}",
		"./lib/**/*.{ts,tsx}",
	],
	theme: {
		extend: {
			colors: {
				ink: "#08111f",
				mist: "#f5fbff",
				accent: "#0f9fca",
				glow: "#6ee7b7",
			},
			boxShadow: {
				panel: "0 24px 80px rgba(8, 17, 31, 0.16)",
			},
		},
	},
	plugins: [],
};

export default config;
