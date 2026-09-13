const http = require("http");
const handler = require("./api/index.js");

const port = Number(process.env.PORT || 5000);

const server = http.createServer((req, res) => {
    handler(req, res).catch(error => {
        console.error(error);
        if (!res.headersSent) {
            res.statusCode = 500;
            res.setHeader("Content-Type", "application/json; charset=utf-8");
        }
        res.end(JSON.stringify({ success: false, message: "Internal server error" }));
    });
});

server.listen(port, () => {
    console.log(`EADS API running at http://localhost:${port}`);
});
