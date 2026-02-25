package engine

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	zen "github.com/gorules/zen-go"
)

type ZenEngine struct {
	engine   zen.Engine // ✅ interface value, BUKAN *zen.Engine
	rulesDir string

	jdmCache *TTLCache[[]byte]
}

func NewZenEngine(rulesDir string) *ZenEngine {
	z := &ZenEngine{
		rulesDir: rulesDir,
		jdmCache: NewTTLCache[[]byte](5 * time.Minute),
	}

	loader := func(key string) ([]byte, error) {
		if b, ok := z.jdmCache.Get(key); ok {
			return b, nil
		}
		b, err := os.ReadFile(filepath.Join(rulesDir, key))
		if err != nil {
			return nil, err
		}
		z.jdmCache.Set(key, b)
		return b, nil
	}

	// ✅ API v0.18.0: NewEngine + EngineConfig
	z.engine = zen.NewEngine(zen.EngineConfig{
		Loader: loader,
	})

	return z
}

func (z *ZenEngine) Close() {
	// ✅ engine interface punya Dispose()
	z.engine.Dispose()
}

// Evaluate menjalankan decisionKey terhadap facts dan mengembalikan output sebagai map[string]any
func (z *ZenEngine) Evaluate(ctx context.Context, decisionKey string, facts map[string]any) (map[string]any, error) {
	_ = ctx // zen-go saat ini belum pakai context

	resp, err := z.engine.Evaluate(decisionKey, facts)
	if err != nil {
		return nil, fmt.Errorf("zen evaluate failed: %w", err)
	}

	// resp.Result adalah JSON bytes (json.RawMessage)
	var out map[string]any
	if err := json.Unmarshal(resp.Result, &out); err != nil {
		return nil, fmt.Errorf("unmarshal zen result failed: %w; raw=%s", err, string(resp.Result))
	}

	return out, nil
}
