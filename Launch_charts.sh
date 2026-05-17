#!/bin/bash

# =========================
# CONFIG
# =========================

DISPLAY=2

TICKERS=(
"AAPL"
"MSFT"
"NVDA"
"SPY"
"TSLA"
"AMZN"
)

# =========================
# GRID POSITIONS
# 2 rows x 3 cols
# =========================

GRIDS=(
"2:3:0:0:1:1"
"2:3:1:0:1:1"
"2:3:2:0:1:1"
"2:3:0:1:1:1"
"2:3:1:1:1:1"
"2:3:2:1:1:1"
)

# =========================
# LAUNCH CHARTS
# =========================

for i in "${!TICKERS[@]}"
do
    TICKER=${TICKERS[$i]}
    GRID=${GRIDS[$i]}

    URL="https://www.tradingview.com/chart/?symbol=${TICKER}&interval=D&theme=dark"

    echo "Launching $TICKER"

    osascript <<EOF
tell application "Safari"
    activate
    
    set newWindow to make new document
    set URL of front document to "$URL"
end tell
EOF

    # wait for window creation
    sleep 0.1

    # get current frontmost Safari window
    WINDOW_ID=$(yabai -m query --windows --window | jq '.id')

    echo "Window ID: $WINDOW_ID"

    # move to monitor
    yabai -m window "$WINDOW_ID" --display $DISPLAY

    # tile into grid
    yabai -m window "$WINDOW_ID" --grid "$GRID"

    sleep 0.1
done

# focus target monitor
yabai -m display --focus $DISPLAY

echo "Done."