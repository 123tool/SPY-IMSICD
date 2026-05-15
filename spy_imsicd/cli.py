import click
import time
import json
import configparser
import os
from datetime import datetime

from .modem import GSMProbe
from .detector import IMSIDetector
from .database import Database
from .logger import Logger
from .alert import AlertSystem
from .sdr_scanner import SDRScanner

@click.group()
def cli():
    """SPY-IMSICD - IMSI Catcher Detector CLI"""
    pass

@cli.command()
@click.option('--config', default='config.ini', help='Config file path')
@click.option('--port', default='/dev/ttyUSB0', help='Modem serial port')
@click.option('--interval', default=10, help='Scan interval (seconds)')
def monitor(config, port, interval):
    """Continuously monitor for IMSI catchers"""
    # Load config
    cfg = configparser.ConfigParser()
    if os.path.exists(config):
        cfg.read(config)
        port = cfg.get('modem', 'port', fallback=port)
        baud = cfg.getint('modem', 'baudrate', fallback=115200)
        opencellid_key = cfg.get('opencellid', 'api_key', fallback=None)
        desktop_notify = cfg.getboolean('alert', 'desktop_notify', fallback=True)
        telegram_token = cfg.get('alert', 'telegram_bot_token', fallback=None)
        telegram_chat = cfg.get('alert', 'telegram_chat_id', fallback=None)
        log_file = cfg.get('logging', 'log_file', fallback='spy_imsicd.log')
        log_level = cfg.get('logging', 'log_level', fallback='INFO')
        export_fmt = cfg.get('logging', 'export_format', fallback='json')
    else:
        baud = 115200
        opencellid_key = None
        desktop_notify = True
        telegram_token = None
        telegram_chat = None
        log_file = "spy_imsicd.log"
        log_level = "INFO"
        export_fmt = "json"

    # Setup
    db = Database()
    alert = AlertSystem(desktop_notify=desktop_notify, telegram_token=telegram_token, telegram_chat_id=telegram_chat)
    detector = IMSIDetector(db, alert, opencellid_key=opencellid_key)
    logger_obj = Logger(log_file, export_fmt)
    modem = GSMProbe(port=port, baudrate=baud)

    if not modem.ser:
        click.echo("ERROR: Could not connect to modem. Exiting.")
        return

    click.echo(f"Starting monitoring every {interval} seconds. Press Ctrl+C to stop.")
    try:
        while True:
            cell = modem.get_serving_cell()
            neighbors = modem.get_neighbor_cells()
            rssi = cell.get("rssi")
            if rssi is not None:
                detector.update(cell, neighbors, rssi)
                # Print status
                status = f"[{datetime.now().strftime('%H:%M:%S')}] Cell: {cell.get('lac')}/{cell.get('cid')} Net: {cell.get('network_type')} RSSI: {rssi} dBm"
                click.echo(status)
            else:
                click.echo("No signal data")
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped.")
    finally:
        modem.close()
        db.close()

@cli.command()
@click.option('--config', default='config.ini')
def scan_once(config):
    """Perform a single scan and display results"""
    cfg = configparser.ConfigParser()
    if os.path.exists(config):
        cfg.read(config)
        port = cfg.get('modem', 'port', fallback='/dev/ttyUSB0')
        baud = cfg.getint('modem', 'baudrate', fallback=115200)
    else:
        port = '/dev/ttyUSB0'
        baud = 115200

    modem = GSMProbe(port, baud)
    if not modem.ser:
        click.echo("Modem connection failed.")
        return
    cell = modem.get_serving_cell()
    neighbors = modem.get_neighbor_cells()
    rssi = cell.get("rssi")
    click.echo(json.dumps(cell, indent=2))
    click.echo(f"Neighbors: {len(neighbors)}")
    modem.close()

@cli.command()
@click.argument('action', type=click.Choice(['add', 'list', 'remove']))
@click.option('--mcc', help='Mobile Country Code')
@click.option('--mnc', help='Mobile Network Code')
@click.option('--lac', type=int, help='Location Area Code')
@click.option('--cid', type=int, help='Cell ID')
@click.option('--reason', default='manual')
def whitelist(action, mcc, mnc, lac, cid, reason):
    """Manage whitelisted cells"""
    db = Database()
    if action == 'add':
        if not all([mcc, mnc, lac is not None, cid is not None]):
            click.echo("Please provide --mcc, --mnc, --lac, --cid")
            return
        db.add_to_whitelist(mcc, mnc, lac, cid, reason)
        click.echo(f"Added {mcc}-{mnc}-{lac}-{cid} to whitelist")
    elif action == 'list':
        # Simple implementation: read from DB directly
        import sqlite3
        conn = sqlite3.connect("spy_imsicd.db")
        cur = conn.cursor()
        cur.execute("SELECT mcc, mnc, lac, cid, reason FROM whitelist")
        rows = cur.fetchall()
        for row in rows:
            click.echo(f"{row[0]}-{row[1]}-{row[2]}-{row[3]}: {row[4]}")
        conn.close()
    elif action == 'remove':
        # Not implemented for brevity
        click.echo("Remove not yet implemented")
    db.close()

@cli.command()
@click.option('--format', 'export_fmt', default='json', help='Export format json/csv')
@click.option('--output', help='Output filename')
def export(format, output):
    """Export detection logs"""
    db = Database()
    logger_obj = Logger(export_format=format)
    detections = db.get_recent_detections(limit=1000)
    logger_obj.export_detections(detections, output)
    db.close()

@cli.command()
def version():
    """Show version"""
    from . import __version__
    click.echo(f"SPY-IMSICD version {__version__}")

if __name__ == "__main__":
    cli()
