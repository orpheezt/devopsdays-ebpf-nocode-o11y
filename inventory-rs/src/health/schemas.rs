use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct HealthStatusResponse {
    pub status: &'static str,
}

impl Default for HealthStatusResponse {
    fn default() -> Self {
        Self { status: "ok" }
    }
}

#[derive(Debug, Serialize)]
pub struct ReadinessStatusResponse {
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub database: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl ReadinessStatusResponse {
    pub fn ok() -> Self {
        Self {
            status: "ok".into(),
            database: Some("connected".into()),
            error: None,
        }
    }

    pub fn error(err: impl Into<String>) -> Self {
        Self {
            status: "error".into(),
            database: Some("disconnected".into()),
            error: Some(err.into()),
        }
    }
}
