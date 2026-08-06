"""
Intent Detector
"""

from core.detectors.inventory_detector import InventoryDetector
from core.detectors.service_detector import ServiceDetector
from core.detectors.cliente_detector import ClienteDetector
from core.detectors.venta_detector import VentaDetector
from core.detectors.proveedor_detector import ProveedorDetector
from core.detectors.contenido_detector import ContenidoDetector
from core.detectors.reporte_detector import ReporteDetector
from core.detectors.evento_detector import EventoDetector
from core.detectors.contabilidad_detector import ContabilidadDetector
from core.detectors.cotizacion_detector import CotizacionDetector
from core.detectors.caja_detector import CajaDetector
from core.detectors.descuento_detector import DescuentoDetector
from core.detectors.garantia_detector import GarantiaDetector
from core.detectors.cuenta_cobrar_detector import CuentaCobrarDetector
from core.detectors.cuenta_pagar_detector import CuentaPagarDetector
from core.detectors.combo_detector import ComboDetector
from core.detectors.unidad_medida_detector import UnidadMedidaDetector
from core.detectors.puntos_detector import PuntosDetector
from core.detectors.codigo_barras_detector import CodigoBarrasDetector
from core.detectors.tarifa_detector import TarifaDetector
from core.detectors.reembolso_detector import ReembolsoDetector
from core.detectors.contenido_foto_detector import ContenidoFotoDetector
from core.command_normalizer import CommandNormalizer


class IntentDetector:

    def __init__(self):

        self.normalizer = CommandNormalizer()

        self.detectors = [

            ContenidoFotoDetector(),
            CajaDetector(),
            ReembolsoDetector(),
            DescuentoDetector(),
            GarantiaDetector(),
            CuentaCobrarDetector(),
            CuentaPagarDetector(),
            ComboDetector(),
            UnidadMedidaDetector(),
            PuntosDetector(),
            CodigoBarrasDetector(),
            CotizacionDetector(),
            ReporteDetector(),
            VentaDetector(),
            ProveedorDetector(),
            EventoDetector(),
            ContabilidadDetector(),
            ContenidoDetector(),
            ClienteDetector(),
            TarifaDetector(),
            ServiceDetector(),
            InventoryDetector()

        ]

    def detect(self, message: str):

        text = self.normalizer.normalize(message)

        for detector in self.detectors:

            result = detector.detect(text)

            if result:

                return result

        return None