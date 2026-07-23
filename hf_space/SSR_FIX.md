# Gradio SSR compatibility

Oyen Purba V0.6 disables Gradio's experimental SSR process in the Space launcher. The live `/render_mp4` API is served directly by Gradio so ZeroGPU requests do not get intercepted by the SSR frontend with HTTP 405.
