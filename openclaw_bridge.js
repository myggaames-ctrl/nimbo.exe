const os = require("os");
const path = require("path");

const { GatewayChatClient } = require(
    path.join(os.homedir(), ".npm-global/lib/node_modules/openclaw/dist/gateway-chat-BNvrNtAY.js")
);

(async () => {

    const message = process.argv.slice(2).join(" ");

    console.log("====================================");
    console.log("[1] Iniciando Bridge");
    console.log("Mensaje:", message);
    console.log("====================================");

    try {

        console.log("[2] Conectando...");

        const client = await GatewayChatClient.connect({});

        console.log("[3] Connect OK");

        client.start();

        console.log("[4] Esperando Ready...");

        await client.waitForReady();

        console.log("[5] Ready OK");

        let response = "";

        client.onEvent = ({ event, payload }) => {

            console.log("------------------------------------");
            console.log("EVENT:", event);
            console.log("STATE:", payload?.state);
            console.log("PAYLOAD:");
            console.dir(payload, { depth: null });
            console.log("------------------------------------");

            if (event !== "chat")
                return;

            if (payload?.state === "delta") {
                response += payload.deltaText || "";
                return;
            }

            if (payload?.state === "final") {

                if (
                    payload.message &&
                    Array.isArray(payload.message.content)
                ) {

                    const finalText = payload.message.content
                        .map(x => x.text || "")
                        .join("")
                        .trim();

                    console.log("FINAL:");
                    console.log(finalText);

                    process.exit(0);
                }

                if (payload.message?.text) {

                    console.log("FINAL:");
                    console.log(payload.message.text.trim());

                    process.exit(0);

                }

                console.log("FINAL (DELTA):");
                console.log(response.trim());

                process.exit(0);

            }

        };

        console.log("[6] Enviando mensaje...");

        await client.sendChat({

            sessionKey: "web-dashboard",

            message

        });

        console.log("[7] sendChat terminó");

        setTimeout(() => {

            console.log("====================================");
            console.log("TIMEOUT");
            console.log("Respuesta acumulada:");
            console.log(response);
            console.log("====================================");

            process.exit(1);

        }, 120000);

    } catch (err) {

        console.log("====================================");
        console.log("ERROR");
        console.error(err);
        console.log("====================================");

        process.exit(1);

    }

})();