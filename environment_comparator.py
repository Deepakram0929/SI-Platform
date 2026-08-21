import base64
import html
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
import yaml

from kubernetes import client
from kubernetes import config as kube_config


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Environment Comparator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

ENVIRONMENTS = [
    "UAT",
    "BLUE",
    "DEV",
    "Green",
    "STAGING",
    "Prod",
]

RESOURCE_TYPES = [
    "ConfigMap",
    "Secret",
    "Deployment",
    "StatefulSet",
]

# Kubernetes API request timeout in seconds.
# Parallel source/destination scans prevent one healthy cluster from
# waiting unnecessarily for the other cluster's response.
# Keeping this configurable avoids long waits when an API endpoint is unhealthy.
KUBE_API_TIMEOUT = 30


# ============================================================
# CSS
# ============================================================

def load_css():

    st.markdown(
        """
        <style>

        .env-title {
            font-size: 30px;
            font-weight: 700;
            color: #17345f;
        }

        .env-subtitle {
            font-size: 14px;
            color: #5f7698;
            margin-bottom: 25px;
        }

        .transfer-box {
            background: #f1f6ff;
            border: 1px solid #a9c9ff;
            border-radius: 9px;
            padding: 16px;
            margin-top: 15px;
            margin-bottom: 20px;
        }

        .cluster-source {
            background: #f1fff6;
            border: 1px solid #9be5b5;
            border-radius: 9px;
            padding: 16px;
        }

        .cluster-destination {
            background: #fff4f5;
            border: 1px solid #f0aab3;
            border-radius: 9px;
            padding: 16px;
        }

        .key-box {
            background: #f6f8fb;
            border-radius: 6px;
            padding: 10px;
            min-height: 38px;
            word-break: break-word;
        }

        .source-value {
            background: #fff4e8;
            border-left: 3px solid #ff7900;
            border-radius: 5px;
            padding: 10px;
            min-height: 38px;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .destination-value {
            background: #edf4ff;
            border-left: 3px solid #377dff;
            border-radius: 5px;
            padding: 10px;
            min-height: 38px;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .same {
            color: #138a3d;
            font-weight: 700;
        }

        .diff {
            color: #d95b00;
            font-weight: 700;
        }

        .empty {
            color: #777777;
            font-weight: 700;
        }

        .missing {
            color: #b46a00;
            font-weight: 700;
        }

        .destination-only {
            color: #3867a8;
            font-weight: 700;
        }

        .resource-card {
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SESSION STATE
# ============================================================

def initialize_state():

    defaults = {
        "ec_source_api": None,
        "ec_destination_api": None,

        "ec_source_version": "",
        "ec_destination_version": "",

        "ec_namespaces": [],

        "ec_results": None,

        "ec_source_env": "BLUE",
        "ec_destination_env": "Green",

        "ec_confirm": False,

        "ec_source_resources": {},
        "ec_destination_resources": {},
        # Global queue of ConfigMap/Secret keys selected for the final update.
        # Structure: {resource_type: {resource_name: [key, ...]}}
        "ec_global_selected": {},
        "ec_global_selection_revision": 0,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# COMMON HELPERS
# ============================================================

def normalize_value(value):

    if value is None:
        return ""

    return str(value)


def is_empty(value):

    return normalize_value(value).strip() == ""


def safe_text(value):

    return html.escape(
        normalize_value(value)
    )


def yaml_text(value):

    try:
        return yaml.safe_dump(
            value,
            sort_keys=True,
            default_flow_style=False,
        ).strip()
    except Exception:
        return normalize_value(value)


def status_css(status):

    return {
        "SAME": "same",
        "DIFF": "diff",
        "EMPTY": "empty",
        "MISSING": "missing",
        "DESTINATION_ONLY": "destination-only",
    }.get(
        status,
        "diff",
    )


def render_status(status):

    css = status_css(status)

    label = status.replace(
        "_",
        " ",
    )

    st.markdown(
        f'<span class="{css}">{safe_text(label)}</span>',
        unsafe_allow_html=True,
    )


def render_value_box(
    value,
    box_class,
):

    st.markdown(
        f"""
        <div class="{box_class}">
            {safe_text(value)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# KUBECONFIG
# ============================================================

def load_kubeconfig(uploaded_file):

    if uploaded_file is None:
        raise ValueError(
            "Kubeconfig file was not uploaded."
        )

    raw = uploaded_file.getvalue()

    if not raw:
        raise ValueError(
            "Uploaded kubeconfig is empty."
        )

    try:

        data = yaml.safe_load(
            raw.decode("utf-8")
        )

    except Exception as exc:

        raise ValueError(
            f"Invalid kubeconfig YAML: {exc}"
        )

    if not isinstance(data, dict):

        raise ValueError(
            "Invalid kubeconfig structure."
        )

    return data


def create_kubernetes_api(
    kubeconfig_data,
):

    api_client = (
        kube_config.new_client_from_config_dict(
            kubeconfig_data
        )
    )

    core_api = client.CoreV1Api(
        api_client
    )

    version_api = client.VersionApi(
        api_client
    )

    apps_api = client.AppsV1Api(
        api_client
    )

    return (
        core_api,
        version_api,
        apps_api,
    )


def get_cluster_version(
    version_api,
):

    try:

        result = version_api.get_code()

        return getattr(
            result,
            "git_version",
            "Unknown",
        )

    except Exception:

        return "Unknown"


# ============================================================
# NAMESPACE
# ============================================================

def get_namespaces(api):

    response = api.list_namespace(
        _request_timeout=KUBE_API_TIMEOUT
    )

    names = []

    for item in response.items or []:

        if (
            item.metadata
            and item.metadata.name
        ):

            names.append(
                item.metadata.name
            )

    return sorted(
        set(names),
        key=str.lower,
    )


# ============================================================
# CONFIGMAP
# ============================================================

def get_all_configmaps(
    api,
    namespace,
):

    configmaps = {}

    continue_token = None

    while True:

        kwargs = {
            "namespace": namespace,
            "_request_timeout": KUBE_API_TIMEOUT,
        }

        if continue_token:

            kwargs["_continue"] = (
                continue_token
            )

        response = (
            api.list_namespaced_config_map(
                **kwargs
            )
        )

        for item in response.items or []:

            if (
                not item.metadata
                or not item.metadata.name
            ):
                continue

            name = item.metadata.name

            data = {}

            if item.data:

                for key, value in (
                    item.data.items()
                ):

                    data[
                        str(key)
                    ] = normalize_value(
                        value
                    )

            if getattr(
                item,
                "binary_data",
                None,
            ):

                for key, value in (
                    item.binary_data.items()
                ):

                    key = str(key)

                    if key not in data:

                        data[key] = (
                            normalize_value(
                                value
                            )
                        )

            configmaps[name] = data

        continue_token = getattr(
            response.metadata,
            "_continue",
            None,
        )

        if not continue_token:
            break

    return configmaps


# ============================================================
# SECRET
# ============================================================

def decode_secret_value(
    value,
):

    if value is None:
        return ""

    try:

        if isinstance(
            value,
            bytes,
        ):

            decoded = base64.b64decode(
                value
            )

        else:

            decoded = base64.b64decode(
                str(value)
            )

        return decoded.decode(
            "utf-8"
        )

    except Exception:

        return normalize_value(
            value
        )


def get_all_secrets(
    api,
    namespace,
):

    secrets = {}

    continue_token = None

    while True:

        kwargs = {
            "namespace": namespace,
            "_request_timeout": KUBE_API_TIMEOUT,
        }

        if continue_token:

            kwargs["_continue"] = (
                continue_token
            )

        response = (
            api.list_namespaced_secret(
                **kwargs
            )
        )

        for item in response.items or []:

            if (
                not item.metadata
                or not item.metadata.name
            ):
                continue

            name = item.metadata.name

            data = {}

            for key, value in (
                (item.data or {}).items()
            ):

                data[
                    str(key)
                ] = decode_secret_value(
                    value
                )

            secrets[name] = data

        continue_token = getattr(
            response.metadata,
            "_continue",
            None,
        )

        if not continue_token:
            break

    return secrets


# ============================================================
# DEPLOYMENT
# ============================================================

def workload_to_fields(
    workload,
):

    fields = {}

    spec = workload.spec

    if spec is None:
        return fields

    fields[
        "spec.replicas"
    ] = normalize_value(
        getattr(
            spec,
            "replicas",
            "",
        )
    )

    fields[
        "spec.strategy"
    ] = yaml_text(
        getattr(
            spec,
            "strategy",
            None,
        ).to_dict()
        if getattr(
            spec,
            "strategy",
            None,
        )
        else {}
    )

    template = getattr(
        spec,
        "template",
        None,
    )

    if template is None:
        return fields

    metadata = getattr(
        template,
        "metadata",
        None,
    )

    if metadata:

        fields[
            "spec.template.metadata.labels"
        ] = yaml_text(
            getattr(
                metadata,
                "labels",
                None,
            )
            or {}
        )

        fields[
            "spec.template.metadata.annotations"
        ] = yaml_text(
            getattr(
                metadata,
                "annotations",
                None,
            )
            or {}
        )

    pod_spec = getattr(
        template,
        "spec",
        None,
    )

    if pod_spec is None:
        return fields

    fields[
        "spec.template.spec.serviceAccountName"
    ] = normalize_value(
        getattr(
            pod_spec,
            "service_account_name",
            "",
        )
    )

    fields[
        "spec.template.spec.nodeSelector"
    ] = yaml_text(
        getattr(
            pod_spec,
            "node_selector",
            None,
        )
        or {}
    )

    fields[
        "spec.template.spec.tolerations"
    ] = yaml_text(
        [
            item.to_dict()
            if hasattr(
                item,
                "to_dict",
            )
            else str(item)
            for item in (
                getattr(
                    pod_spec,
                    "tolerations",
                    None,
                )
                or []
            )
        ]
    )

    fields[
        "spec.template.spec.affinity"
    ] = yaml_text(
        getattr(
            pod_spec,
            "affinity",
            None,
        ).to_dict()
        if getattr(
            pod_spec,
            "affinity",
            None,
        )
        else {}
    )

    containers = (
        getattr(
            pod_spec,
            "containers",
            None,
        )
        or []
    )

    for container in containers:

        cname = normalize_value(
            getattr(
                container,
                "name",
                "",
            )
        )

        if not cname:
            continue

        fields[
            f"container.{cname}.image"
        ] = normalize_value(
            getattr(
                container,
                "image",
                "",
            )
        )

        fields[
            f"container.{cname}.imagePullPolicy"
        ] = normalize_value(
            getattr(
                container,
                "image_pull_policy",
                "",
            )
        )

        env_data = {}

        for env in (
            getattr(
                container,
                "env",
                None,
            )
            or []
        ):

            env_name = normalize_value(
                getattr(
                    env,
                    "name",
                    "",
                )
            )

            if not env_name:
                continue

            env_value = getattr(
                env,
                "value",
                None,
            )

            if env_value is not None:

                env_data[
                    env_name
                ] = normalize_value(
                    env_value
                )

            else:

                value_from = getattr(
                    env,
                    "value_from",
                    None,
                )

                if value_from:

                    env_data[
                        env_name
                    ] = yaml_text(
                        value_from.to_dict()
                        if hasattr(
                            value_from,
                            "to_dict",
                        )
                        else str(
                            value_from
                        )
                    )

        fields[
            f"container.{cname}.env"
        ] = yaml_text(
            env_data
        )

        resources = getattr(
            container,
            "resources",
            None,
        )

        fields[
            f"container.{cname}.resources"
        ] = yaml_text(
            {
                "limits": (
                    getattr(
                        resources,
                        "limits",
                        None,
                    )
                    or {}
                ),
                "requests": (
                    getattr(
                        resources,
                        "requests",
                        None,
                    )
                    or {}
                ),
            }
        )

        fields[
            f"container.{cname}.ports"
        ] = yaml_text(
            [
                port.to_dict()
                if hasattr(
                    port,
                    "to_dict",
                )
                else str(port)
                for port in (
                    getattr(
                        container,
                        "ports",
                        None,
                    )
                    or []
                )
            ]
        )

    fields[
        "spec.template.spec.volumes"
    ] = yaml_text(
        [
            volume.to_dict()
            if hasattr(
                volume,
                "to_dict",
            )
            else str(volume)
            for volume in (
                getattr(
                    pod_spec,
                    "volumes",
                    None,
                )
                or []
            )
        ]
    )

    return fields


def get_all_workloads(
    apps_api,
    namespace,
    resource_type,
):

    if resource_type == "Deployment":

        response = (
            apps_api.list_namespaced_deployment(
                namespace=namespace,
                _request_timeout=KUBE_API_TIMEOUT,
            )
        )

    elif resource_type == "StatefulSet":

        response = (
            apps_api.list_namespaced_stateful_set(
                namespace=namespace,
                _request_timeout=KUBE_API_TIMEOUT,
            )
        )

    else:

        return {}

    result = {}

    for item in response.items or []:

        if (
            item.metadata
            and item.metadata.name
        ):

            result[
                item.metadata.name
            ] = workload_to_fields(
                item
            )

    return result


# ============================================================
# GENERIC KEY/VALUE COMPARISON
# ============================================================

def compare_key_value_resources(
    source_resources,
    destination_resources,
):

    source_names = set(
        source_resources.keys()
    )

    destination_names = set(
        destination_resources.keys()
    )

    all_names = sorted(
        source_names
        | destination_names,
        key=str.lower,
    )

    summary = {
        "source_count": len(
            source_names
        ),
        "destination_count": len(
            destination_names
        ),
        "common": len(
            source_names
            & destination_names
        ),
        "missing": len(
            source_names
            - destination_names
        ),
        "destination_only": len(
            destination_names
            - source_names
        ),
        "same": 0,
        "diff": 0,
        "empty": 0,
        "missing_keys": 0,
        "destination_only_keys": 0,
    }

    results = []

    for name in all_names:

        source_exists = (
            name in source_resources
        )

        destination_exists = (
            name in destination_resources
        )

        source_data = (
            source_resources.get(
                name,
                {},
            )
        )

        destination_data = (
            destination_resources.get(
                name,
                {},
            )
        )

        if (
            source_exists
            and not destination_exists
        ):

            resource_status = (
                "MISSING"
            )

        elif (
            destination_exists
            and not source_exists
        ):

            resource_status = (
                "DESTINATION_ONLY"
            )

        else:

            resource_status = "NORMAL"

        all_keys = sorted(
            set(source_data.keys())
            | set(destination_data.keys()),
            key=str.lower,
        )

        fields = []

        for key in all_keys:

            source_key_exists = (
                key in source_data
            )

            destination_key_exists = (
                key in destination_data
            )

            source_value = normalize_value(
                source_data.get(
                    key,
                    "",
                )
            )

            destination_value = normalize_value(
                destination_data.get(
                    key,
                    "",
                )
            )

            if (
                source_key_exists
                and not destination_key_exists
            ):

                status = "MISSING"

                summary[
                    "missing_keys"
                ] += 1

            elif (
                destination_key_exists
                and not source_key_exists
            ):

                status = (
                    "DESTINATION_ONLY"
                )

                summary[
                    "destination_only_keys"
                ] += 1

            elif (
                is_empty(
                    source_value
                )
                and is_empty(
                    destination_value
                )
            ):

                status = "EMPTY"

                summary[
                    "empty"
                ] += 1

            elif (
                source_value
                == destination_value
            ):

                status = "SAME"

                summary[
                    "same"
                ] += 1

            else:

                status = "DIFF"

                summary[
                    "diff"
                ] += 1

            fields.append(
                {
                    "key": key,
                    "source_value": source_value,
                    "destination_value": destination_value,
                    "source_exists": source_key_exists,
                    "destination_exists": destination_key_exists,
                    "status": status,
                }
            )

        results.append(
            {
                "name": name,
                "source_exists": source_exists,
                "destination_exists": destination_exists,
                "resource_status": resource_status,
                "fields": fields,
            }
        )

    return (
        results,
        summary,
    )


# ============================================================
# WORKLOAD COMPARISON
# ============================================================

def compare_workloads(
    source_resources,
    destination_resources,
):

    return compare_key_value_resources(
        source_resources,
        destination_resources,
    )


# ============================================================
# CONFIGMAP UPDATE
# ============================================================

def patch_configmap(
    api,
    namespace,
    name,
    source_data,
    selected_keys,
):

    patch_data = {}

    for key in selected_keys:

        if key in source_data:

            patch_data[
                key
            ] = normalize_value(
                source_data[key]
            )

    if not patch_data:

        return (
            False,
            "No ConfigMap keys selected.",
        )

    try:

        api.patch_namespaced_config_map(
            name=name,
            namespace=namespace,
            body={
                "data": patch_data
            },
            _request_timeout=KUBE_API_TIMEOUT,
        )

        return (
            True,
            f"Updated {len(patch_data)} ConfigMap key(s).",
        )

    except Exception as exc:

        return (
            False,
            str(exc),
        )


# ============================================================
# SECRET UPDATE
# ============================================================

def patch_secret(
    api,
    namespace,
    name,
    source_data,
    selected_keys,
):

    patch_data = {}

    for key in selected_keys:

        if key not in source_data:
            continue

        value = normalize_value(
            source_data[key]
        )

        patch_data[
            key
        ] = base64.b64encode(
            value.encode("utf-8")
        ).decode(
            "ascii"
        )

    if not patch_data:

        return (
            False,
            "No Secret keys selected.",
        )

    try:

        api.patch_namespaced_secret(
            name=name,
            namespace=namespace,
            body={
                "data": patch_data
            },
            _request_timeout=KUBE_API_TIMEOUT,
        )

        return (
            True,
            f"Updated {len(patch_data)} Secret key(s).",
        )

    except Exception as exc:

        return (
            False,
            str(exc),
        )


# ============================================================
# RESOURCE HEADER
# ============================================================

def resource_title(
    resource_type,
    namespace,
    item,
):

    status = item[
        "resource_status"
    ]

    if status == "MISSING":

        icon = "🟡"

    elif status == "DESTINATION_ONLY":

        icon = "🔵"

    else:

        icon = "🟠"

    return (
        f"{icon} "
        f"{status.replace('_', ' ')} | "
        f"{namespace} | "
        f"{resource_type} | "
        f"{item['name']} | "
        f"{len(item['fields'])} field(s)"
    )


def resource_has_actionable_changes(item):
    """Return True when a resource contains actionable differences."""
    if item.get("resource_status") in ("MISSING", "DESTINATION_ONLY"):
        return True

    return any(
        field.get("status") in (
            "DIFF",
            "MISSING",
            "DESTINATION_ONLY",
        )
        for field in item.get("fields", [])
    )


# ============================================================
# FAST TABLE RENDERING
# ============================================================

def build_actionable_dataframe(resource_type, results, show_only_differences=True):
    """Build one compact table instead of hundreds of Streamlit widgets."""
    rows = []

    for item in results:
        destination_exists = item.get("destination_exists", False)

        for field in item.get("fields", []):
            status = field.get("status", "")

            if show_only_differences and status not in (
                "DIFF",
                "MISSING",
                "DESTINATION_ONLY",
            ):
                continue

            can_update = (
                resource_type in ("ConfigMap", "Secret")
                and destination_exists
                and status in ("DIFF", "MISSING")
            )

            rows.append({
                # Never pre-select actionable DIFF/MISSING fields.
                "Select": False,
                "Resource": item["name"],
                "Key / Field": field["key"],
                "Source Value": normalize_value(field.get("source_value", "")),
                "Destination Value": normalize_value(field.get("destination_value", "")),
                "Status": status,
                "_can_update": can_update,
            })

    return rows


def style_comparison_table(df):
    """Apply original comparator-style colors to the comparison table."""
    def style_columns(data):
        styles = pd.DataFrame("", index=data.index, columns=data.columns)

        if "Key / Field" in data.columns:
            styles["Key / Field"] = (
                "background-color:#f6f8fb; color:#17345f; font-weight:500;"
            )

        if "Source Value" in data.columns:
            styles["Source Value"] = (
                "background-color:#fff4e8; color:#5a3a18; "
                "border-left:3px solid #ff7900;"
            )

        if "Destination Value" in data.columns:
            styles["Destination Value"] = (
                "background-color:#edf4ff; color:#17345f; "
                "border-left:3px solid #377dff;"
            )

        if "Status" in data.columns:
            status_styles = []
            for status in data["Status"]:
                if status == "SAME":
                    status_styles.append(
                        "background-color:#eaf8ef; color:#138a3d; font-weight:700;"
                    )
                elif status == "DIFF":
                    status_styles.append(
                        "background-color:#fff1e6; color:#d95b00; font-weight:700;"
                    )
                elif status == "MISSING":
                    status_styles.append(
                        "background-color:#fff8df; color:#b46a00; font-weight:700;"
                    )
                elif status == "DESTINATION_ONLY":
                    status_styles.append(
                        "background-color:#edf4ff; color:#3867a8; font-weight:700;"
                    )
                else:
                    status_styles.append("")
            styles["Status"] = status_styles

        return styles

    styler = df.style.apply(style_columns, axis=None)
    styler.set_properties(**{
        "font-size": "13px",
        "vertical-align": "top",
        "white-space": "pre-wrap",
    })
    styler.set_table_styles([
        {
            "selector": "th",
            "props": [
                ("background-color", "#f6f8fb"),
                ("color", "#17345f"),
                ("font-weight", "700"),
                ("border-bottom", "1px solid #d7dde7"),
            ],
        },
        {
            "selector": "td",
            "props": [
                ("padding", "8px"),
                ("border-bottom", "1px solid #e5e9f0"),
            ],
        },
    ])
    return styler


def render_fast_comparison_table(
    resource_type,
    namespace,
    results,
    show_only_differences=True,
    select_all=False,
):
    """Render one fast, color-coded comparison table per Kubernetes resource.

    Selection is intentionally local to the resource until the user clicks
    "Add Selected Changes to Global Update".  This keeps the table responsive
    while allowing a single global update queue at the bottom of the page.
    """
    if not results:
        st.info(f"No {resource_type} resources found.")
        return {}, False

    submitted_any = False
    scan_generation = st.session_state.get("ec_scan_generation", 0)

    for item_index, item in enumerate(results):
        fields = []
        destination_exists = item.get("destination_exists", False)

        for field in item.get("fields", []):
            status = field.get("status", "")

            if show_only_differences and status not in (
                "DIFF",
                "MISSING",
                "DESTINATION_ONLY",
            ):
                continue

            can_update = (
                resource_type in ("ConfigMap", "Secret")
                and destination_exists
                and status in ("DIFF", "MISSING")
            )

            fields.append({
                "Select": False,
                "Key / Field": field["key"],
                "Source Value": normalize_value(field.get("source_value", "")),
                "Destination Value": normalize_value(field.get("destination_value", "")),
                "Status": status,
                "_can_update": can_update,
            })

        if not fields:
            continue

        resource_name = item["name"]
        resource_status = item.get("resource_status", "NORMAL")
        title = resource_title(resource_type, namespace, item)

        # Local selection is stored by resource so that "Select All DIFF" etc.
        # affects only this table.
        local_key = (
            f"ec_local_selected_{resource_type}_{namespace}_{resource_name}"
        )
        local_selected = set(st.session_state.get(local_key, []))

        selectable_keys = {
            row["Key / Field"]
            for row in fields
            if row["_can_update"]
        }

        # Remove stale keys after a new scan / filter change.
        local_selected &= selectable_keys
        st.session_state[local_key] = sorted(local_selected)

        with st.expander(title, expanded=False):
            if resource_status == "MISSING":
                st.warning(
                    f"This {resource_type} exists in the source cluster but does "
                    "not exist in the destination. It will NOT be created automatically."
                )
            elif resource_status == "DESTINATION_ONLY":
                st.info(
                    f"This {resource_type} exists only in the destination cluster. "
                    "It will NOT be deleted."
                )

            actionable = sum(1 for row in fields if row["_can_update"])
            st.caption(
                f"{resource_type}: {len(fields)} displayed field(s) | "
                f"{actionable} selectable DIFF/MISSING field(s)."
            )

            # One-click selection controls for THIS resource/table.
            b1, b2, b3, b4 = st.columns(4)

            with b1:
                select_diff = st.button(
                    "☑ Select All DIFF",
                    key=f"ec_sel_diff_{resource_type}_{namespace}_{item_index}_{scan_generation}",
                    use_container_width=True,
                    disabled=not any(
                        row["Status"] == "DIFF" and row["_can_update"]
                        for row in fields
                    ),
                )

            with b2:
                select_missing = st.button(
                    "☑ Select All MISSING",
                    key=f"ec_sel_missing_{resource_type}_{namespace}_{item_index}_{scan_generation}",
                    use_container_width=True,
                    disabled=not any(
                        row["Status"] == "MISSING" and row["_can_update"]
                        for row in fields
                    ),
                )

            with b3:
                select_both = st.button(
                    "☑ Select DIFF + MISSING",
                    key=f"ec_sel_both_{resource_type}_{namespace}_{item_index}_{scan_generation}",
                    use_container_width=True,
                    disabled=not selectable_keys,
                )

            with b4:
                clear_local = st.button(
                    "☐ Clear Selection",
                    key=f"ec_clear_local_{resource_type}_{namespace}_{item_index}_{scan_generation}",
                    use_container_width=True,
                    disabled=not local_selected,
                )

            if select_diff:
                local_selected = {
                    row["Key / Field"]
                    for row in fields
                    if row["Status"] == "DIFF" and row["_can_update"]
                }
                st.session_state[local_key] = sorted(local_selected)
                st.rerun()

            if select_missing:
                local_selected = {
                    row["Key / Field"]
                    for row in fields
                    if row["Status"] == "MISSING" and row["_can_update"]
                }
                st.session_state[local_key] = sorted(local_selected)
                st.rerun()

            if select_both:
                local_selected = selectable_keys.copy()
                st.session_state[local_key] = sorted(local_selected)
                st.rerun()

            if clear_local:
                st.session_state[local_key] = []
                st.rerun()

            # Build the editor from the current local selection so one-click
            # buttons visibly tick every applicable row.
            display_fields = []
            for row in fields:
                row_copy = row.copy()
                row_copy["Select"] = (
                    row_copy["Key / Field"] in local_selected
                    and row_copy["_can_update"]
                )
                display_fields.append(row_copy)

            df = pd.DataFrame(display_fields)
            visible = [
                "Select",
                "Key / Field",
                "Source Value",
                "Destination Value",
                "Status",
            ]

            styled_df = style_comparison_table(df[visible])

            editor_key = (
                f"ec_resource_editor_{resource_type}_"
                f"{namespace}_{item_index}_{scan_generation}_"
                f"{st.session_state.get('ec_global_selection_revision', 0)}"
            )

            edited = st.data_editor(
                styled_df,
                key=editor_key,
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                height=min(520, max(120, 45 + len(df) * 32)),
                disabled=[
                    "Key / Field",
                    "Source Value",
                    "Destination Value",
                    "Status",
                ],
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select this DIFF/MISSING key for the global destination update.",
                        default=False,
                    ),
                    "Key / Field": st.column_config.TextColumn(
                        "Key / Field", width="medium"
                    ),
                    "Source Value": st.column_config.TextColumn(
                        "Source Value", width="large"
                    ),
                    "Destination Value": st.column_config.TextColumn(
                        "Destination Value", width="large"
                    ),
                    "Status": st.column_config.TextColumn(
                        "Status", width="small"
                    ),
                },
            )

            # Read manual checkbox changes from the editor and persist them.
            edited_df = df[visible].copy()
            if isinstance(edited, dict) and "edited_rows" in edited:
                for row_index, changes in edited.get("edited_rows", {}).items():
                    if row_index >= len(edited_df):
                        continue
                    for column, value in changes.items():
                        if column in edited_df.columns:
                            edited_df.at[row_index, column] = value
            elif isinstance(edited, pd.DataFrame):
                edited_df = edited.copy()

            current_selected = {
                str(row["Key / Field"])
                for _, row in edited_df.iterrows()
                if bool(row.get("Select", False))
                and row.get("Status") in ("DIFF", "MISSING")
                and row["Key / Field"] in selectable_keys
            }

            if current_selected != set(st.session_state.get(local_key, [])):
                st.session_state[local_key] = sorted(current_selected)

            st.caption(
                f"Currently selected in this table: "
                f"{len(current_selected)} key(s)."
            )

            add_col, clear_col = st.columns([3, 1])

            with add_col:
                add_to_global = st.button(
                    (
                        f"➕ Add {len(current_selected)} Selected Changes "
                        f"to Global Update"
                    ),
                    type="primary",
                    use_container_width=True,
                    key=f"ec_add_global_{resource_type}_{namespace}_{item_index}_{scan_generation}",
                    disabled=not current_selected,
                )

            with clear_col:
                clear_after_add = st.button(
                    "🗑️ Clear Table",
                    use_container_width=True,
                    key=f"ec_clear_after_{resource_type}_{namespace}_{item_index}_{scan_generation}",
                    disabled=not current_selected,
                )

            if add_to_global:
                global_selected = st.session_state.setdefault(
                    "ec_global_selected", {}
                )
                type_queue = global_selected.setdefault(resource_type, {})
                existing = set(type_queue.get(resource_name, []))
                type_queue[resource_name] = sorted(
                    existing | current_selected
                )
                st.session_state["ec_global_selection_revision"] += 1
                submitted_any = True
                st.success(
                    f"Added {len(current_selected)} key(s) from "
                    f"{resource_name} to the global update queue."
                )

            if clear_after_add:
                st.session_state[local_key] = []
                st.rerun()

    return {}, submitted_any


# ============================================================
# GET SELECTED RESOURCE KEYS
# ============================================================

def get_selected_keys(
    resource_type,
    namespace,
    results,
    select_all=False,
):

    selected = {}

    # Fast path for Select All: resolve the selection directly from the
    # comparison result instead of reading hundreds of checkbox states.
    if select_all and resource_type in (
        "ConfigMap",
        "Secret",
    ):
        for item in results:
            if not item.get("destination_exists"):
                continue

            keys = [
                field["key"]
                for field in item.get("fields", [])
                if field.get("status") in (
                    "DIFF",
                    "MISSING",
                )
            ]

            if keys:
                selected[item["name"]] = keys

        return selected

    if resource_type not in (
        "ConfigMap",
        "Secret",
    ):

        return selected

    for item in results:

        if not item[
            "destination_exists"
        ]:

            continue

        name = item[
            "name"
        ]

        for index, field in enumerate(
            item["fields"]
        ):

            if field[
                "status"
            ] not in (
                "DIFF",
                "MISSING",
            ):

                continue

            checkbox_key = (
                f"ec_select_"
                f"{resource_type}_"
                f"{namespace}_"
                f"{name}_"
                f"{index}"
            )

            if st.session_state.get(
                checkbox_key,
                False,
            ):

                selected.setdefault(
                    name,
                    [],
                ).append(
                    field["key"]
                )

    return selected


# ============================================================
# UPDATE SELECTED RESOURCE
# ============================================================

def render_global_update_queue(
    namespace,
    resources,
    destination_api,
):
    """Render one final global queue and allow removing unwanted updates.

    Users can review everything selected from every ConfigMap/Secret, untick
    individual entries they do not want to update, remove them from the queue,
    then explicitly confirm the remaining entries before patching.
    """
    global_selected = st.session_state.get("ec_global_selected", {})

    # Build a flat queue from the per-resource selection dictionaries.
    queue_rows = []
    for resource_type, selected_by_resource in global_selected.items():
        if resource_type not in ("ConfigMap", "Secret"):
            continue

        resource_result = resources.get(resource_type, {})
        source_data = resource_result.get("source", {})

        for name, keys in selected_by_resource.items():
            for key in keys:
                queue_rows.append({
                    "Update": True,
                    "Resource Type": resource_type,
                    "Resource": name,
                    "Key": key,
                    "Source Value": normalize_value(
                        source_data.get(name, {}).get(key, "")
                    ),
                })

    if not queue_rows:
        return

    st.divider()
    st.markdown("## 🚀 Global Update Destination")

    st.success(
        f"{len(queue_rows)} selected key(s) are queued for destination update."
    )

    st.info(
        "Review the final list below. Untick any key you do NOT want to update. "
        "Only checked rows will be updated in the destination."
    )

    queue_df = pd.DataFrame(queue_rows)

    queue_editor_key = (
        f"ec_global_update_editor_{st.session_state.get('ec_scan_generation', 0)}_"
        f"{st.session_state.get('ec_global_selection_revision', 0)}"
    )

    edited_queue = st.data_editor(
        queue_df,
        key=queue_editor_key,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        height=min(650, max(150, 48 + len(queue_df) * 35)),
        disabled=[
            "Resource Type",
            "Resource",
            "Key",
            "Source Value",
        ],
        column_config={
            "Update": st.column_config.CheckboxColumn(
                "Update",
                help="Keep checked to update this key in the destination.",
                default=True,
            ),
            "Resource Type": st.column_config.TextColumn(
                "Resource Type", width="small"
            ),
            "Resource": st.column_config.TextColumn(
                "Resource", width="medium"
            ),
            "Key": st.column_config.TextColumn(
                "Key", width="medium"
            ),
            "Source Value": st.column_config.TextColumn(
                "Source Value", width="large"
            ),
        },
    )

    # Resolve the current checked state.
    final_queue = queue_df.copy()
    if isinstance(edited_queue, dict) and "edited_rows" in edited_queue:
        for row_index, changes in edited_queue.get("edited_rows", {}).items():
            if row_index >= len(final_queue):
                continue
            for column, value in changes.items():
                if column in final_queue.columns:
                    final_queue.at[row_index, column] = value
    elif isinstance(edited_queue, pd.DataFrame):
        final_queue = edited_queue.copy()

    checked_count = int(final_queue["Update"].fillna(False).astype(bool).sum())

    st.caption(
        f"{checked_count} key(s) currently selected for the final destination update."
    )

    remove_col, clear_col = st.columns(2)

    with remove_col:
        if st.button(
            "🗑️ Remove Unticked / Unwanted Keys",
            use_container_width=True,
            key="ec_remove_unwanted_global",
        ):
            new_global = {}

            for _, row in final_queue.iterrows():
                if not bool(row.get("Update", False)):
                    continue

                rtype = row["Resource Type"]
                name = row["Resource"]
                key = row["Key"]

                new_global.setdefault(rtype, {}).setdefault(name, []).append(key)

            for rtype in new_global:
                for name in new_global[rtype]:
                    new_global[rtype][name] = sorted(
                        set(new_global[rtype][name])
                    )

            st.session_state["ec_global_selected"] = new_global
            st.session_state["ec_global_selection_revision"] += 1
            st.rerun()

    with clear_col:
        if st.button(
            "🧹 Clear Global Update Queue",
            use_container_width=True,
            key="ec_clear_global_queue",
        ):
            st.session_state["ec_global_selected"] = {}
            st.session_state["ec_global_selection_revision"] += 1
            st.rerun()

    if checked_count == 0:
        st.warning(
            "No keys are selected for update. Tick at least one row to continue."
        )
        return

    st.warning(
        "⚠️ The following checked keys will be updated in the destination "
        "using the source values."
    )

    confirm = st.checkbox(
        "I confirm that the checked ConfigMap/Secret source values should be updated in the destination.",
        key="ec_global_confirm",
    )

    if not confirm:
        return

    if st.button(
        "🚀 Update Checked Keys in Destination",
        type="primary",
        use_container_width=True,
        key="ec_global_update_button",
    ):
        success = 0
        failed = 0

        # Group the checked queue back by resource type/resource.
        update_groups = {}
        for _, row in final_queue.iterrows():
            if not bool(row.get("Update", False)):
                continue

            rtype = row["Resource Type"]
            name = row["Resource"]
            key = row["Key"]

            update_groups.setdefault(rtype, {}).setdefault(name, []).append(key)

        messages = []

        for rtype, selected_by_resource in update_groups.items():
            resource_result = resources.get(rtype, {})
            source_data = resource_result.get("source", {})

            for name, keys in selected_by_resource.items():
                try:
                    if rtype == "ConfigMap":
                        ok, message = patch_configmap(
                            destination_api,
                            namespace,
                            name,
                            source_data.get(name, {}),
                            keys,
                        )
                    elif rtype == "Secret":
                        ok, message = patch_secret(
                            destination_api,
                            namespace,
                            name,
                            source_data.get(name, {}),
                            keys,
                        )
                    else:
                        ok = False
                        message = f"{rtype} updates are disabled."

                    if ok:
                        success += len(keys)
                    else:
                        failed += len(keys)

                    messages.append(
                        f"{rtype}/{name}: {message}"
                    )
                except Exception as exc:
                    failed += len(keys)
                    messages.append(
                        f"{rtype}/{name}: {exc}"
                    )

        if failed == 0:
            st.success(
                f"All {success} checked key(s) were updated successfully "
                "in the destination."
            )
            # Clear only after a successful update.
            st.session_state["ec_global_selected"] = {}
            st.session_state["ec_global_selection_revision"] += 1
        else:
            st.warning(
                f"Update completed. Successful keys: {success}. "
                f"Failed keys: {failed}."
            )

        if messages:
            with st.expander("Update details", expanded=False):
                for message in messages:
                    st.write(message)


# ============================================================
# RESOURCE METRICS
# ============================================================

def render_summary(
    resource_type,
    summary,
):

    st.markdown(
        f"### {resource_type} Summary"
    )

    cols = st.columns(
        7
    )

    metrics = [
        (
            "SOURCE",
            summary[
                "source_count"
            ],
        ),
        (
            "DESTINATION",
            summary[
                "destination_count"
            ],
        ),
        (
            "COMMON",
            summary[
                "common"
            ],
        ),
        (
            "SAME",
            summary[
                "same"
            ],
        ),
        (
            "DIFF",
            summary[
                "diff"
            ],
        ),
        (
            "MISSING",
            summary[
                "missing"
            ],
        ),
        (
            "DESTINATION ONLY",
            summary[
                "destination_only"
            ],
        ),
    ]

    for column, (
        label,
        value,
    ) in zip(
        cols,
        metrics,
    ):

        with column:

            st.metric(
                label,
                value,
            )


# ============================================================
# PARALLEL RESOURCE FETCH
# ============================================================

def fetch_source_destination_parallel(
    source_fetcher,
    destination_fetcher,
):
    """Fetch source and destination Kubernetes data concurrently.

    The two Kubernetes API calls are independent, so running them in
    parallel reduces scan time when both clusters are reachable.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        source_future = executor.submit(source_fetcher)
        destination_future = executor.submit(destination_fetcher)

        source = source_future.result()
        destination = destination_future.result()

    return source, destination


# ============================================================
# SCAN ONE RESOURCE
# ============================================================

def scan_resource(
    resource_type,
    source_api,
    destination_api,
    source_apps_api,
    destination_apps_api,
    namespace,
):

    # --------------------------------------------------------
    # CONFIGMAP
    # --------------------------------------------------------

    if resource_type == "ConfigMap":

        source, destination = fetch_source_destination_parallel(
            lambda: get_all_configmaps(source_api, namespace),
            lambda: get_all_configmaps(destination_api, namespace),
        )

        results, summary = (
            compare_key_value_resources(
                source,
                destination,
            )
        )

        return (
            source,
            destination,
            results,
            summary,
        )

    # --------------------------------------------------------
    # SECRET
    # --------------------------------------------------------

    if resource_type == "Secret":

        source, destination = fetch_source_destination_parallel(
            lambda: get_all_secrets(source_api, namespace),
            lambda: get_all_secrets(destination_api, namespace),
        )

        results, summary = (
            compare_key_value_resources(
                source,
                destination,
            )
        )

        return (
            source,
            destination,
            results,
            summary,
        )

    # --------------------------------------------------------
    # DEPLOYMENT
    # --------------------------------------------------------

    if resource_type == "Deployment":

        source, destination = fetch_source_destination_parallel(
            lambda: get_all_workloads(
                source_apps_api,
                namespace,
                "Deployment",
            ),
            lambda: get_all_workloads(
                destination_apps_api,
                namespace,
                "Deployment",
            ),
        )

        results, summary = (
            compare_workloads(
                source,
                destination,
            )
        )

        return (
            source,
            destination,
            results,
            summary,
        )

    # --------------------------------------------------------
    # STATEFULSET
    # --------------------------------------------------------

    if resource_type == "StatefulSet":

        source, destination = fetch_source_destination_parallel(
            lambda: get_all_workloads(
                source_apps_api,
                namespace,
                "StatefulSet",
            ),
            lambda: get_all_workloads(
                destination_apps_api,
                namespace,
                "StatefulSet",
            ),
        )

        results, summary = (
            compare_workloads(
                source,
                destination,
            )
        )

        return (
            source,
            destination,
            results,
            summary,
        )

    raise ValueError(
        f"Unsupported resource type: "
        f"{resource_type}"
    )


# ============================================================
# MAIN APPLICATION
# ============================================================

def render_environment_comparator():

    initialize_state()

    load_css()

    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        '<div class="env-title">'
        '🔍 Environment Comparator'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="env-subtitle">'
        'Compare Kubernetes resources between '
        'two clusters and selectively synchronize '
        'ConfigMap or Secret values.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    st.markdown(
        "## Environment"
    )

    source_col, destination_col = (
        st.columns(2)
    )

    with source_col:

        source_env = st.selectbox(
            "Source",
            ENVIRONMENTS,
            index=(
                ENVIRONMENTS.index(
                    st.session_state.get(
                        "ec_source_env",
                        "BLUE",
                    )
                )
                if st.session_state.get(
                    "ec_source_env",
                    "BLUE",
                ) in ENVIRONMENTS
                else 0
            ),
            key="ec_source_env_select",
        )

    with destination_col:

        destination_options = [
            env
            for env in ENVIRONMENTS
            if env != source_env
        ]

        current_destination = (
            st.session_state.get(
                "ec_destination_env",
                "Green",
            )
        )

        destination_index = (
            destination_options.index(
                current_destination
            )
            if current_destination
            in destination_options
            else 0
        )

        destination_env = st.selectbox(
            "Destination",
            destination_options,
            index=destination_index,
            key="ec_destination_env_select",
        )

    st.session_state[
        "ec_source_env"
    ] = source_env

    st.session_state[
        "ec_destination_env"
    ] = destination_env

    # ========================================================
    # TRANSFER DIRECTION
    # ========================================================

    st.markdown(
        """
        <div class="transfer-box">
            <b>Transfer Direction</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    direction_col1, direction_arrow, direction_col2 = (
        st.columns(
            [
                1,
                0.15,
                1,
            ]
        )
    )

    with direction_col1:

        st.success(
            f"🟢 {source_env}"
        )

    with direction_arrow:

        st.markdown(
            "<br>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "➡️"
        )

    with direction_col2:

        st.error(
            f"🔴 {destination_env}"
        )

    # ========================================================
    # KUBECONFIG
    # ========================================================

    source_col, destination_col = (
        st.columns(2)
    )

    with source_col:

        st.markdown(
            f"### 🟢 {source_env} Cluster"
        )

        st.write(
            f"Upload kubeconfig for "
            f"{source_env}"
        )

        source_file = st.file_uploader(
            f"{source_env} kubeconfig",
            type=[
                "yaml",
                "yml",
                "conf",
            ],
            key="ec_source_file",
        )

    with destination_col:

        st.markdown(
            f"### 🔴 {destination_env} Cluster"
        )

        st.write(
            f"Upload kubeconfig for "
            f"{destination_env}"
        )

        destination_file = st.file_uploader(
            f"{destination_env} kubeconfig",
            type=[
                "yaml",
                "yml",
                "conf",
            ],
            key="ec_destination_file",
        )

    # ========================================================
    # CONNECT
    # ========================================================

    connect_col, refresh_col = (
        st.columns(2)
    )

    with connect_col:

        connect = st.button(
            "🔗 Connect to Both Clusters",
            type="primary",
            use_container_width=True,
            key="ec_connect_button",
        )

    with refresh_col:

        refresh = st.button(
            "🔄 Refresh Namespace List",
            use_container_width=True,
            key="ec_refresh_button",
        )

    # ========================================================
    # CONNECT ACTION
    # ========================================================

    if connect:

        if (
            source_file is None
            or destination_file is None
        ):

            st.error(
                "Please upload both kubeconfig files."
            )

        else:

            try:

                with st.spinner(
                    "Connecting to both clusters..."
                ):

                    source_config = (
                        load_kubeconfig(
                            source_file
                        )
                    )

                    destination_config = (
                        load_kubeconfig(
                            destination_file
                        )
                    )

                    (
                        source_api,
                        source_version_api,
                        source_apps_api,
                    ) = create_kubernetes_api(
                        source_config
                    )

                    (
                        destination_api,
                        destination_version_api,
                        destination_apps_api,
                    ) = create_kubernetes_api(
                        destination_config
                    )

                    source_version = (
                        get_cluster_version(
                            source_version_api
                        )
                    )

                    destination_version = (
                        get_cluster_version(
                            destination_version_api
                        )
                    )

                    source_namespaces = (
                        get_namespaces(
                            source_api
                        )
                    )

                    destination_namespaces = (
                        get_namespaces(
                            destination_api
                        )
                    )

                    common_namespaces = sorted(
                        set(
                            source_namespaces
                        )
                        & set(
                            destination_namespaces
                        ),
                        key=str.lower,
                    )

                    st.session_state[
                        "ec_source_api"
                    ] = source_api

                    st.session_state[
                        "ec_destination_api"
                    ] = destination_api

                    st.session_state[
                        "ec_source_apps_api"
                    ] = source_apps_api

                    st.session_state[
                        "ec_destination_apps_api"
                    ] = destination_apps_api

                    st.session_state[
                        "ec_source_version"
                    ] = source_version

                    st.session_state[
                        "ec_destination_version"
                    ] = destination_version

                    st.session_state[
                        "ec_namespaces"
                    ] = common_namespaces

                    st.session_state[
                        "ec_results"
                    ] = None

                st.success(
                    "Both clusters connected successfully."
                )

            except Exception as exc:

                st.error(
                    "Unable to connect to one or both clusters."
                )

                st.exception(
                    exc
                )

    # ========================================================
    # REFRESH NAMESPACES
    # ========================================================

    if refresh:

        source_api = (
            st.session_state.get(
                "ec_source_api"
            )
        )

        destination_api = (
            st.session_state.get(
                "ec_destination_api"
            )
        )

        if (
            source_api is None
            or destination_api is None
        ):

            st.warning(
                "Connect to both clusters first."
            )

        else:

            try:

                with st.spinner(
                    "Refreshing namespaces..."
                ):

                    source_namespaces = (
                        get_namespaces(
                            source_api
                        )
                    )

                    destination_namespaces = (
                        get_namespaces(
                            destination_api
                        )
                    )

                    common_namespaces = sorted(
                        set(
                            source_namespaces
                        )
                        & set(
                            destination_namespaces
                        ),
                        key=str.lower,
                    )

                    st.session_state[
                        "ec_namespaces"
                    ] = common_namespaces

                st.success(
                    "Namespace list refreshed."
                )

            except Exception as exc:

                st.error(
                    f"Unable to refresh namespaces: "
                    f"{exc}"
                )

    # ========================================================
    # CONNECTED STATUS
    # ========================================================

    source_api = (
        st.session_state.get(
            "ec_source_api"
        )
    )

    destination_api = (
        st.session_state.get(
            "ec_destination_api"
        )
    )

    source_apps_api = (
        st.session_state.get(
            "ec_source_apps_api"
        )
    )

    destination_apps_api = (
        st.session_state.get(
            "ec_destination_apps_api"
        )
    )

    if (
        source_api is not None
        and destination_api is not None
    ):

        st.success(
            f"🟢 {source_env} connected | "
            f"Kubernetes "
            f"{st.session_state.get('ec_source_version', 'Unknown')}"
        )

        st.success(
            f"🟢 {destination_env} connected | "
            f"Kubernetes "
            f"{st.session_state.get('ec_destination_version', 'Unknown')}"
        )

    # ========================================================
    # NAMESPACE
    # ========================================================

    namespaces = (
        st.session_state.get(
            "ec_namespaces",
            [],
        )
    )

    if not namespaces:

        if (
            source_api is not None
            and destination_api is not None
        ):

            st.warning(
                "No common namespaces found."
            )

        return

    st.markdown(
        "## 📁 Namespace"
    )

    selected_namespace = st.selectbox(
        "Select namespace",
        namespaces,
        key="ec_selected_namespace",
    )

    # ========================================================
    # RESOURCE TYPE
    # ========================================================

    st.markdown(
        "## Resource Types"
    )

    selected_resources = st.multiselect(
        "Select resources to compare",
        RESOURCE_TYPES,
        default=[
            "ConfigMap"
        ],
        key="ec_resource_selection",
    )

    st.caption(
        "Select one or more Kubernetes resource "
        "types from the namespace."
    )

    # ========================================================
    # SAFETY
    # ========================================================

    st.warning(
        "🛡️ Safety: ConfigMaps and Secrets are "
        "never automatically created or deleted. "
        "Only explicitly selected DIFF/MISSING "
        "ConfigMap or Secret keys can be updated. "
        "Deployments and StatefulSets are "
        "comparison-only."
    )

    # ========================================================
    # PERFORMANCE / DISPLAY
    # ========================================================

    show_only_differences = st.checkbox(
        "⚡ Show only DIFF / MISSING / DESTINATION ONLY fields",
        value=True,
        key="ec_show_only_differences",
        help=(
            "Recommended for large ConfigMaps/Secrets. "
            "Hides unchanged fields to keep the Streamlit page fast."
        ),
    )

    # ========================================================
    # SCAN
    # ========================================================

    scan = st.button(
        f"🔍 Scan {source_env} → {destination_env}",
        type="primary",
        use_container_width=True,
        key="ec_scan_button",
    )

    # ========================================================
    # SCAN ACTION
    # ========================================================

    if scan:

        if not selected_resources:

            st.error(
                "Please select at least one resource type."
            )

            return

        if (
            source_api is None
            or destination_api is None
        ):

            st.error(
                "Please connect to both clusters first."
            )

            return

        if (
            source_apps_api is None
            or destination_apps_api is None
        ):

            st.error(
                "Kubernetes Apps API is not initialized."
            )

            return

        all_results = {}
        scan_start = time.perf_counter()

        # Clear selections from an earlier scan.
        st.session_state["ec_global_selected"] = {}
        st.session_state["ec_global_selection_revision"] = 0
        for key in list(st.session_state.keys()):
            if (
                key.startswith("ec_pending_selected_")
                or key.startswith("ec_local_selected_")
            ):
                del st.session_state[key]

        try:

            with st.spinner(
                f"Scanning namespace "
                f"'{selected_namespace}'..."
            ):

                for resource_type in (
                    selected_resources
                ):
                    resource_start = time.perf_counter()

                    (
                        source_data,
                        destination_data,
                        results,
                        summary,
                    ) = scan_resource(
                        resource_type,
                        source_api,
                        destination_api,
                        source_apps_api,
                        destination_apps_api,
                        selected_namespace,
                    )

                    resource_elapsed = (
                        time.perf_counter() - resource_start
                    )

                    all_results[
                        resource_type
                    ] = {
                        "source": source_data,
                        "destination": destination_data,
                        "results": results,
                        "summary": summary,
                        "scan_time": resource_elapsed,
                    }

            total_elapsed = time.perf_counter() - scan_start

            # New generation guarantees that a fresh scan starts with no
            # stale checkbox/editor selections from a previous scan.
            st.session_state[
                "ec_scan_generation"
            ] = time.time_ns()

            st.session_state[
                "ec_results"
            ] = {
                "namespace": selected_namespace,
                "resources": all_results,
                "scan_time": total_elapsed,
            }

            st.success(
                f"Scan completed successfully in "
                f"{total_elapsed:.2f} seconds."
            )

            timing_text = " | ".join(
                f"{resource_type}: "
                f"{data['scan_time']:.2f}s"
                for resource_type, data in all_results.items()
            )
            if timing_text:
                st.caption(f"⏱️ API + comparison time: {timing_text}")

        except Exception as exc:

            st.error(
                "Resource scan failed."
            )

            st.exception(
                exc
            )

            return

    # ========================================================
    # RESULTS
    # ========================================================

    stored = (
        st.session_state.get(
            "ec_results"
        )
    )

    if stored is None:

        return

    namespace = stored[
        "namespace"
    ]

    resources = stored[
        "resources"
    ]

    # ========================================================
    # RESULTS HEADER
    # ========================================================

    st.markdown(
        "## Resource Differences"
    )

    st.caption(
        f"Namespace: `{namespace}`"
    )

    # ========================================================
    # RENDER EACH RESOURCE
    # ========================================================

    for resource_type in (
        selected_resources
    ):

        if resource_type not in resources:
            continue

        resource_result = (
            resources[
                resource_type
            ]
        )

        source_data = (
            resource_result[
                "source"
            ]
        )

        destination_data = (
            resource_result[
                "destination"
            ]
        )

        results = (
            resource_result[
                "results"
            ]
        )

        summary = (
            resource_result[
                "summary"
            ]
        )

        st.divider()

        st.markdown(
            f"## {resource_type}"
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        render_summary(
            resource_type,
            summary,
        )

        # ----------------------------------------------------
        # INFORMATION
        # ----------------------------------------------------

        if resource_type in (
            "ConfigMap",
            "Secret",
        ):

            if show_only_differences:
                st.caption(
                    "⚡ Performance mode: unchanged SAME/EMPTY fields are "
                    "hidden. Disable the checkbox above to view all fields."
                )

            st.info(
                f"{resource_type}: "
                "SAME means source and destination "
                "values are identical. "
                "DIFF means both exist but values differ. "
                "MISSING means the source key does not "
                "exist in destination. "
                "DESTINATION ONLY means the key exists "
                "only in destination."
            )

        else:

            st.info(
                f"{resource_type}: "
                "Comparison only. "
                "SAME means the normalized field values "
                "match. DIFF means they differ. "
                "No automatic workload updates are performed."
            )

        # ----------------------------------------------------
        # FAST COMPARISON TABLE
        # ----------------------------------------------------

        if resource_type in ("ConfigMap", "Secret"):

            selectable_count = sum(
                1
                for item in results
                if item.get("destination_exists")
                for field in item.get("fields", [])
                if field.get("status") in ("DIFF", "MISSING")
            )

            st.caption(
                f"{selectable_count} DIFF/MISSING key(s) are available. "
                "Nothing is selected by default; select only the keys you want to update."
            )
            select_all = False

        else:
            select_all = False

        # Hide unchanged resources in performance mode.
        if show_only_differences:
            render_results = [
                item for item in results
                if resource_has_actionable_changes(item)
            ]

            hidden_count = len(results) - len(render_results)
            if hidden_count:
                st.caption(
                    f"⚡ {hidden_count} unchanged resource(s) hidden in performance mode."
                )
        else:
            render_results = results

        if not render_results:
            st.success(
                f"No differences found for {resource_type} in this namespace."
            )
            continue

        if resource_type in ("ConfigMap", "Secret"):
            # Each resource table has its own one-click DIFF/MISSING selection
            # controls. Selections are added to one global queue below.
            render_fast_comparison_table(
                resource_type,
                namespace,
                render_results,
                show_only_differences=show_only_differences,
                select_all=False,
            )

        else:
            # Workloads are comparison-only; a single dataframe is much faster
            # than rendering a row of Streamlit columns for every field.
            rows = []
            for item in render_results:
                for field in item.get("fields", []):
                    if show_only_differences and field.get("status") not in (
                        "DIFF",
                        "MISSING",
                        "DESTINATION_ONLY",
                    ):
                        continue
                    rows.append({
                        "Resource": item["name"],
                        "Field": field["key"],
                        "Source": field.get("source_value", ""),
                        "Destination": field.get("destination_value", ""),
                        "Status": field.get("status", ""),
                    })

            if rows:
                st.dataframe(
                    pd.DataFrame(rows),
                    hide_index=True,
                    use_container_width=True,
                    height=min(650, max(180, 45 + len(rows) * 35)),
                )

    # ========================================================
    # GLOBAL UPDATE QUEUE
    # ========================================================
    # Render after all resource tables so the user can review,
    # remove unwanted entries, confirm once, and update once.
    render_global_update_queue(
        namespace,
        resources,
        destination_api,
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    render_environment_comparator()