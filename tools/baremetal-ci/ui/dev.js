const next = require("next")
const express = require("express")
const { createProxyMiddleware } = require('http-proxy-middleware');

const port = 8080;
const app = next({ dev: true })
app.prepare().then(() => {
    const server = express()

    server.use("/api", createProxyMiddleware({
        target: "http://localhost:8000",
        changeOrigin: true
    }))

    server.all("*", (req, res) => {
        const handle = app.getRequestHandler()
        return handle(req, res)
    })

    server.listen(port, err => {
        if (err) throw err
        console.log(`Listening on http://localhost:${port}`)
    })
})
