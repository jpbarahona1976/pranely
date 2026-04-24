#!/bin/sh
pg_dump -U pranely -d pranely_dev -Fc -f /tmp/pranely_final.dump
ls -la /tmp/pranely_final.dump
