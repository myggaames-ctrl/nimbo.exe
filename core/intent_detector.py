"""
Intent Detector
"""

from core.detectors.inventory_detector import InventoryDetector
from core.detectors.windows_detector import WindowsDetector
from core.detectors.customer_detector import CustomerDetector
from core.detectors.budget_detector import BudgetDetector
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
from core.detectors.combo_detector import ComboDetector
from core.detectors.unidad_medida_detector import UnidadMedidaDetector
from core.detectors.puntos_detector import PuntosDetector
from core.detectors.codigo_barras_detector import CodigoBarrasDetector
from core.detectors.tarifa_detector import TarifaDetector
from core.command_normalizer import CommandNormalizer


class IntentDetector:

    def __init__(self):

        self.normalizer = CommandNormalizer()

        self.detectors = [

            CajaDetector(),
            DescuentoDetector(),
            GarantiaDetector(),
            CuentaCobrarDetector(),
            ComboDetector(),
            UnidadMedidaDetector(),
            PuntosDetector(),
            CodigoBarrasDetector(),
            CotizacionDetector(),
            VentaDetector(),
            ProveedorDetector(),
            ReporteDetector(),
            EventoDetector(),
            ContabilidadDetector(),
            ContenidoDetector(),
            ClienteDetector(),
            TarifaDetector(),
            ServiceDetector(),
            InventoryDetector(),
            BudgetDetector(),
            WindowsDetector()

        ]

    def detect(self, message: str):

        text = self.normalizer.normalize(message)

        for detector in self.detectors:

            result = detector.detect(text)

            if result:

                return result

        return None