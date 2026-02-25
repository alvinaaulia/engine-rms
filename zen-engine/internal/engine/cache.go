package engine

import (
	"sync"
	"time"
)

type cacheItem[T any] struct {
	val       T
	expiresAt time.Time
}

type TTLCache[T any] struct {
	mu    sync.RWMutex
	ttl   time.Duration
	items map[string]cacheItem[T]
}

func NewTTLCache[T any](ttl time.Duration) *TTLCache[T] {
	return &TTLCache[T]{
		ttl:   ttl,
		items: make(map[string]cacheItem[T]),
	}
}

func (c *TTLCache[T]) Get(key string) (T, bool) {
	c.mu.RLock()
	it, ok := c.items[key]
	c.mu.RUnlock()

	var zero T
	if !ok {
		return zero, false
	}
	if time.Now().After(it.expiresAt) {
		c.mu.Lock()
		delete(c.items, key)
		c.mu.Unlock()
		return zero, false
	}
	return it.val, true
}

func (c *TTLCache[T]) Set(key string, val T) {
	c.mu.Lock()
	c.items[key] = cacheItem[T]{val: val, expiresAt: time.Now().Add(c.ttl)}
	c.mu.Unlock()
}

func (c *TTLCache[T]) Delete(key string) {
	c.mu.Lock()
	delete(c.items, key)
	c.mu.Unlock()
}
