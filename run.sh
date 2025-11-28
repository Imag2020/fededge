#!/bin/bash
source venv/bin/activate && nohup python run_server.py &
tail -f nohup.out
