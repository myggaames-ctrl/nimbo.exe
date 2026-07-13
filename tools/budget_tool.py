"""
Herramienta de Presupuestos
"""

from services.budget_service import BudgetService
from services.customer_service import CustomerService
from core.tool_registry import register
from core import responses
from core.workspace import workspace
from services.inventory import InventoryService
from core.event_bus import event_bus

budget = BudgetService()
customers = CustomerService()
inventory = InventoryService()


def create_budget(customer_name):

    customer = customers.get_by_name(customer_name)

    if customer is None:

        return responses.error(
            f"No encontré un cliente llamado '{customer_name}'."
        )

    budget_id = budget.create(
        customer["Id"]
    )

    # ----------------------------------------
    # Guardar presupuesto activo
    # ----------------------------------------

    workspace.set(
        "active_budget_id",
        budget_id
    )

    workspace.set(
        "active_customer_id",
        customer["Id"]
    )

    workspace.set(
        "active_customer_name",
        customer["Name"]
    )

    return responses.success(
        f"""Presupuesto #{budget_id} creado correctamente.

Cliente: {customer['Name']}

Estado: EN_EDICION

Productos: 0

Total: Q0.00"""
    )


register(
    "budget.create",
    create_budget
)

# ==========================================
# MOSTRAR PRESUPUESTO
# ==========================================

def show_budget(_):

    budget_id = workspace.get(
        "active_budget_id"
    )

    if budget_id is None:

        return responses.error(
            "No hay un presupuesto activo."
        )

    current_budget = budget.get(
        budget_id
    )

    if current_budget is None:

        return responses.error(
            "El presupuesto no existe."
        )

    items = budget.items(
        budget_id
    )

    customer_name = workspace.get(
        "active_customer_name"
    )

    return responses.budget(
        current_budget,
        customer_name,
        items
    )


register(
    "budget.show",
    show_budget
)

# ==========================================
# AGREGAR PRODUCTO
# ==========================================

def add_budget_item(query):

    budget_id = workspace.get(
        "active_budget_id"
    )

    if budget_id is None:

        return responses.error(
            "No hay un presupuesto activo."
        )

    products = inventory.search(query)

    if not products:

        return responses.error(
            f"No encontré productos con '{query}'."
        )

    if len(products) > 1:

        return responses.products(products)

    product = products[0]

    budget.add_item(
        budget_id,
        product
    )

    workspace.set(
    "last_product",
    product
    )
    
    event_bus.emit(
        "budget.item_added",
        {
            "budget_id": budget_id,
            "product": product
        }
    )

    return responses.success(
    f"""Producto agregado correctamente.

📦 {product['Name']}

Cantidad: 1

Precio: Q{product['Price']:.2f}

Subtotal: Q{product['Price']:.2f}"""
    )


register(
    "budget.add_item",
    add_budget_item
)