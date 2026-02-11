"""
Application Configuration
=========================
Loads settings from environment variables with validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, AliasChoices
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """
    # ==========================================
    # Application
    # ==========================================
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "PE OrgAIR Platform"
    APP_VERSION: str = "1.0.0"
    
    # ==========================================
    # Snowflake (Optional for testing, required for production)
    # ==========================================
    snowflake_account: Optional[str] = None
    snowflake_user: Optional[str] = None
    snowflake_password: Optional[str] = None
    snowflake_database: str = "PE_ORGAIR_DB"
    snowflake_schema: str = "PE_ORGAIR_SCHEMA"
    snowflake_warehouse: str = "PE_ORGAIR_WH"
    snowflake_role: Optional[str] = "ACCOUNTADMIN"
    
    # ==========================================
    # Redis
    # ==========================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    
    # ==========================================
    # AWS S3
    # ==========================================
    aws_access_key_id: Optional[str] = Field(
        default=None, 
        validation_alias=AliasChoices("AWS_ACCESS_KEY_ID", "aws_access_key_id")
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "aws_secret_access_key")
    )
    aws_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("AWS_REGION", "aws_region")
    )
    s3_bucket: Optional[str] = Field(
        default=None, 
        validation_alias=AliasChoices("S3_BUCKET", "s3_bucket", "S3_BUCKET_NAME")
    )
    s3_prefix: str = Field(
        default="",
        validation_alias=AliasChoices("S3_PREFIX", "s3_prefix")
    )

    # ==========================================
    # SEC EDGAR
    # ==========================================
    SEC_EDGAR_USER_AGENT_EMAIL: str = Field(
        default="your-email@example.com",
        validation_alias=AliasChoices("SEC_EDGAR_USER_AGENT_EMAIL", "sec_edgar_user_agent_email")
    )
    SEC_SLEEP_SECONDS: float = 0.75
    
    # ==========================================
    # USPTO API (for CS2 - Patent signals)
    # ==========================================
    uspto_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("USPTO_API_KEY", "uspto_api_key")
    )
    
    # ==========================================
    # API Settings
    # ==========================================
    api_version: str = "1.0.0"
    
    # ==========================================
    # Computed Properties
    # ==========================================
    
    @property
    def resolved_s3_bucket(self) -> str:
        """
        Return S3 bucket name, raise if not configured.
        Used by S3Storage class.
        """
        if not self.s3_bucket:
            raise ValueError(
                "S3_BUCKET is not configured. "
                "Set S3_BUCKET environment variable or add to .env file."
            )
        return self.s3_bucket
    
    @property
    def resolved_aws_region(self) -> str:
        """
        Return AWS region.
        Used by S3Storage class.
        """
        return self.aws_region
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.APP_ENV.lower() in ("production", "prod")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.APP_ENV.lower() in ("development", "dev")
    
    # ==========================================
    # Validators
    # ==========================================
    
    @model_validator(mode="after")
    def require_snowflake_in_production(self):
        """Ensure Snowflake credentials are set in production"""
        if self.is_production:
            missing = [
                k for k in [
                    "snowflake_account",
                    "snowflake_user",
                    "snowflake_password",
                ]
                if getattr(self, k) in (None, "")
            ]
            if missing:
                raise ValueError(
                    f"Missing Snowflake settings in production: {missing}. "
                    f"Please set these in your .env file."
                )
        return self
    
    @model_validator(mode="after")
    def validate_aws_credentials(self):
        """Warn if AWS credentials are missing"""
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            # Only warn if S3 bucket is configured (meaning they want to use S3)
            if self.s3_bucket:
                print("⚠️  WARNING: S3_BUCKET is set but AWS credentials are missing!")
                print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance to avoid repeated env loading.
    Use this function to get settings throughout the application.
    """
    return Settings()


# Global settings instance
settings = get_settings()


# ==========================================
# Quick validation on import
# ==========================================
if __name__ == "__main__":
    """Test settings loading"""
    print("=" * 60)
    print("SETTINGS VALIDATION")
    print("=" * 60)
    print(f"Environment: {settings.APP_ENV}")
    print(f"Debug: {settings.DEBUG}")
    print(f"Snowflake Account: {settings.snowflake_account or 'Not set'}")
    print(f"AWS Region: {settings.aws_region}")
    print(f"S3 Bucket: {settings.s3_bucket or 'Not set'}")
    print(f"S3 Prefix: {settings.s3_prefix or '(none)'}")
    print(f"SEC Email: {settings.SEC_EDGAR_USER_AGENT_EMAIL}")
    print("=" * 60)
    
    # Test computed properties
    try:
        bucket = settings.resolved_s3_bucket
        print(f"✅ S3 bucket resolved: {bucket}")
    except ValueError as e:
        print(f"❌ S3 bucket error: {e}")
    
    print("=" * 60)