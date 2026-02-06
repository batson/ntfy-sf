# Deployment Guide

## Strategy

This app runs as a **scheduled job** on Fly.io's free tier:
- GitHub Actions triggers the job every 5 minutes
- Fly.io machine starts, runs the check, sends notifications, then stops
- State persists between runs using a Fly.io volume
- Completely free on Fly.io + GitHub Actions free tiers

## Prerequisites

1. Fly.io account (free tier)
2. GitHub repository for this code
3. Fly CLI installed locally: `brew install flyctl` (or see [Fly.io docs](https://fly.io/docs/hands-on/install-flyctl/))

## Step 1: Initial Fly.io Setup

```bash
# Login to Fly.io
fly auth login

# Create the app (don't deploy yet)
fly apps create sf-dispatch-monitor --org personal

# Create persistent volume for state
fly volumes create state_data --region sjc --size 1 --app sf-dispatch-monitor

# Set environment secrets
fly secrets set NTFY_TOPIC="sf-dispatch-alerts-3190" --app sf-dispatch-monitor

# Deploy the app
fly deploy --ha=false
```

## Step 2: GitHub Actions Setup

1. Get your Fly.io API token:
   ```bash
   fly auth token
   ```

2. Add it to GitHub repository secrets:
   - Go to your GitHub repo → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `FLY_API_TOKEN`
   - Value: [paste token from step 1]

3. Commit and push the `.github/workflows/scheduled-check.yml` file

4. The workflow will now run every 5 minutes automatically!

## Step 3: Verify Deployment

```bash
# Check machine status
fly machines list --app sf-dispatch-monitor

# View logs
fly logs --app sf-dispatch-monitor

# Manually trigger a run (for testing)
gh workflow run scheduled-check.yml
```

## Monitoring

- **GitHub Actions**: Check the "Actions" tab in your repo to see each run
- **Fly.io logs**: `fly logs --app sf-dispatch-monitor`
- **State file**: The `/data/.last_state.json` file persists between runs

## Cost

- **Fly.io**: Free tier includes enough resources for this (machine only runs ~5 seconds every 5 minutes)
- **GitHub Actions**: Free tier includes 2,000 minutes/month (this uses ~10 minutes/month)
- **Total**: $0/month ✨

## Troubleshooting

### Machine won't start
```bash
# Check machine status
fly machines list --app sf-dispatch-monitor

# If stuck, destroy and recreate
fly machine destroy [MACHINE_ID] --app sf-dispatch-monitor
fly deploy --ha=false
```

### Volume issues
```bash
# List volumes
fly volumes list --app sf-dispatch-monitor

# If needed, recreate volume (will lose state)
fly volumes destroy state_data --app sf-dispatch-monitor
fly volumes create state_data --region sjc --size 1 --app sf-dispatch-monitor
```

### Check state file
```bash
fly ssh console --app sf-dispatch-monitor
cat /data/.last_state.json
```
