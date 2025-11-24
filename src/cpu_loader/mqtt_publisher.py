"""
MQTT Publisher Module
Publishes CPU load control settings and metrics to MQTT broker.
"""

import json
import logging
import os
from typing import Dict, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """Handles publishing CPU load data to MQTT broker."""

    def __init__(
        self,
        broker_host: Optional[str] = None,
        broker_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        topic_prefix: Optional[str] = None,
        client_id: Optional[str] = None,
    ):
        """
        Initialize MQTT publisher.

        Args:
            broker_host: MQTT broker hostname (env: MQTT_BROKER_HOST)
            broker_port: MQTT broker port (env: MQTT_BROKER_PORT, default: 1883)
            username: MQTT username (env: MQTT_USERNAME)
            password: MQTT password (env: MQTT_PASSWORD)
            topic_prefix: Topic prefix (env: MQTT_TOPIC_PREFIX, default: cpu-loader)
            client_id: MQTT client ID (env: MQTT_CLIENT_ID, default: cpu-loader)
        """
        if mqtt is None:
            raise ImportError(
                "paho-mqtt not installed. Install with: pip install paho-mqtt"
            )

        # Get settings from arguments or environment variables
        self.broker_host = broker_host or os.getenv("MQTT_BROKER_HOST")
        self.broker_port = int(
            broker_port or int(os.getenv("MQTT_BROKER_PORT", "1883"))
        )
        self.username = username or os.getenv("MQTT_USERNAME")
        self.password = password or os.getenv("MQTT_PASSWORD")
        self.topic_prefix = topic_prefix or os.getenv("MQTT_TOPIC_PREFIX", "cpu-loader")
        self.client_id = client_id or os.getenv("MQTT_CLIENT_ID", "cpu-loader")

        self.client: Optional[mqtt.Client] = None
        self.connected = False

        # Only connect if broker host is provided
        if self.broker_host:
            self._connect()
        else:
            logger.info("MQTT broker host not configured, MQTT publishing disabled")

    def _connect(self):
        """Connect to MQTT broker."""
        try:
            # Create MQTT client
            self.client = mqtt.Client(
                client_id=self.client_id,
                protocol=mqtt.MQTTv311,
            )

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            # Set credentials if provided
            if self.username:
                self.client.username_pw_set(self.username, self.password)

            # Connect to broker
            logger.info(
                f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}"
            )
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)

            # Start network loop in background thread
            self.client.loop_start()

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.client = None

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnect from MQTT broker: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")

    def publish_load_settings(self, num_threads: int, loads: Dict[int, float]):
        """
        Publish load control settings to MQTT.

        Args:
            num_threads: Number of active threads
            loads: Dictionary mapping thread ID to load percentage
        """
        if not self.connected or not self.client:
            return

        try:
            # Calculate average load
            avg_load = sum(loads.values()) / len(loads) if loads else 0.0

            # Prepare payload
            payload = {
                "num_threads": num_threads,
                "loads": loads,
                "average_load": round(avg_load, 2),
            }

            # Publish to topic
            topic = f"{self.topic_prefix}/load_settings"
            self.client.publish(
                topic,
                json.dumps(payload),
                qos=1,
                retain=True,
            )
            logger.debug(f"Published load settings to {topic}")

        except Exception as e:
            logger.error(f"Failed to publish load settings: {e}")

    def publish_cpu_metrics(
        self,
        total_cpu_percent: float,
        per_cpu_percent: list,
        cpu_temperature: Optional[float] = None,
    ):
        """
        Publish CPU metrics to MQTT.

        Args:
            total_cpu_percent: Total CPU utilization percentage
            per_cpu_percent: List of per-CPU utilization percentages
            cpu_temperature: CPU temperature in Celsius (optional)
        """
        if not self.connected or not self.client:
            return

        try:
            # Prepare payload
            payload = {
                "total_cpu_percent": round(total_cpu_percent, 1),
                "per_cpu_percent": [round(cpu, 1) for cpu in per_cpu_percent],
            }

            # Add temperature if available
            if cpu_temperature is not None:
                payload["cpu_temperature"] = cpu_temperature

            # Publish to topic
            topic = f"{self.topic_prefix}/cpu_metrics"
            self.client.publish(
                topic,
                json.dumps(payload),
                qos=0,
                retain=False,
            )
            logger.debug(f"Published CPU metrics to {topic}")

        except Exception as e:
            logger.error(f"Failed to publish CPU metrics: {e}")

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT broker: {e}")
            finally:
                self.client = None
                self.connected = False
