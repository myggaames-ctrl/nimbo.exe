"""
Herramienta de Clientes
"""

from services.customer_service import CustomerService
from core.tool_registry import register
from core import responses

customer = CustomerService()


# ==========================================
# CREAR
# ==========================================

def create_customer(name):

    customer.create(name)

    return responses.success(
        f"Cliente '{name}' creado correctamente."
    )


register(
    "customer.create",
    create_customer
)


# ==========================================
# BUSCAR
# ==========================================

def search_customer(text):

    customers = customer.search(text)

    return responses.customers(customers)


register(
    "customer.search",
    search_customer
)


# ==========================================
# LISTAR
# ==========================================

def list_customers(_):

    customers = customer.list()

    return responses.customers(customers)


register(
    "customer.list",
    list_customers
)

# ==========================================
# ELIMINAR
# ==========================================

def delete_customer(name):

    deleted = customer.delete(name)

    if deleted == 0:

        return responses.error(
            f"No encontré un cliente llamado '{name}'."
        )

    return responses.success(
        f"Cliente '{name}' eliminado correctamente."
    )


register(
    "customer.delete",
    delete_customer
)

# ==========================================
# EDITAR
# ==========================================

def update_customer(data):

    if " a " not in data:

        return responses.error(
            "Usa: editar cliente <nombre actual> a <nombre nuevo>"
        )

    old_name, new_name = data.split(" a ", 1)

    updated = customer.update(
        old_name.strip(),
        new_name.strip()
    )

    if updated == 0:

        return responses.error(
            f"No encontré un cliente llamado '{old_name}'."
        )

    return responses.success(
        f"Cliente actualizado a '{new_name}'."
    )


register(
    "customer.update",
    update_customer
)   