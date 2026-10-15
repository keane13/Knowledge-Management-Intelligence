$ProjectID = "smooth-reason-491707-f6"

Write-Host "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project $ProjectID

$EnvFilePath = ".env.local"
if (-Not (Test-Path $EnvFilePath)) {
    Write-Host "Error: .env.local not found!" -ForegroundColor Red
    exit 1
}

$KeysToSecret = @("OPENAI_API_KEY", "WEAVIATE_URL", "WEAVIATE_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT", "HUGGINGFACE_TOKEN")

foreach ($Key in $KeysToSecret) {
    # Extract value from .env.local
    # This regex handles simple key=value pairs, removing spaces and quotes
    $Line = Get-Content $EnvFilePath | Where-Object { $_ -match "^$Key\s*=" }
    if ($Line) {
        $Value = $Line -replace "^$Key\s*=\s*`"?(.*?)`"?\s*$", '$1'
        
        Write-Host "Processing $Key..."
        
        # Check if secret exists
        $SecretExists = gcloud secrets describe $Key --project=$ProjectID 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Creating secret $Key..."
            gcloud secrets create $Key --replication-policy="automatic" --project=$ProjectID
        }
        
        # Add a new version
        Write-Host "Adding new version to $Key..."
        # Using a temporary file to avoid issues with echoing newlines/special chars
        $TempFile = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($TempFile, $Value)
        gcloud secrets versions add $Key --data-file=$TempFile --project=$ProjectID
        Remove-Item $TempFile
        
        Write-Host "Successfully stored $Key" -ForegroundColor Green
    } else {
        Write-Host "Warning: $Key not found in $EnvFilePath" -ForegroundColor Yellow
    }
}

Write-Host "Done setting up secrets!" -ForegroundColor Green
