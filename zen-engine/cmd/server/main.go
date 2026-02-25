package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"rule-engine-zen/internal/engine"
	"rule-engine-zen/internal/httpapi"
	"rule-engine-zen/internal/version"
)

func main() {
	rulesDir := os.Getenv("RULES_DIR")
	if rulesDir == "" {
		rulesDir = "./rules_published"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	zenEngine := engine.NewZenEngine(rulesDir)
	defer zenEngine.Close()

	vp := version.NewDBProvider() // stub (ENV). Ganti ke DB beneran nanti.

	h := httpapi.NewHandler(zenEngine, vp)

	mux := http.NewServeMux()
	h.Routes(mux)

	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}

	log.Printf("rule-engine-zen listening on :%s (rulesDir=%s)", port, rulesDir)
	log.Fatal(srv.ListenAndServe())
}
