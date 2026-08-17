package health

type HealthStatusResponse struct {
	Status string `json:"status"`
}

type ReadinessStatusResponse struct {
	Status   string `json:"status"`
	Database string `json:"database,omitempty"`
	Error    string `json:"error,omitempty"`
}
