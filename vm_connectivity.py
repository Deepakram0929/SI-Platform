import streamlit as st
import pandas as pd
import paramiko
import tempfile
import os

from kubernetes import client
from kubernetes.config import load_kube_config


# ============================================================
# GET RKE1 NODES
# ============================================================

def get_rke1_nodes(kubeconfig_bytes):
    """
    Read RKE1 Kubernetes nodes and their InternalIP.
    """

    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".yaml",
            delete=False,
        ) as f:
            f.write(kubeconfig_bytes)
            temp_file = f.name

        # Load kubeconfig
        load_kube_config(
            config_file=temp_file
        )

        core_api = client.CoreV1Api()

        nodes = core_api.list_node().items

        result = []

        for node in nodes:

            node_name = node.metadata.name
            internal_ip = None

            for address in node.status.addresses or []:

                if address.type == "InternalIP":
                    internal_ip = address.address
                    break

            if internal_ip:
                result.append(
                    {
                        "node": node_name,
                        "ip": internal_ip,
                    }
                )

        return result, None

    except Exception as exc:
        return [], str(exc)

    finally:

        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


# ============================================================
# SSH CONNECT
# ============================================================

def connect_ssh(
    ip,
    username,
    password,
    timeout=10,
):
    """
    Create one SSH connection to a source VM.
    """

    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    try:

        ssh.connect(
            hostname=ip,
            username=username,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )

        return ssh, None

    except Exception as exc:

        return None, str(exc)


# ============================================================
# TEST ALL DESTINATIONS FROM ONE SOURCE VM
# ============================================================

def test_all_from_source(
    source_ip,
    destinations,
    username,
    password,
):
    """
    SSH to the source VM once.

    Then ping every destination VM from that source VM.
    """

    results = {}

    ssh, error = connect_ssh(
        ip=source_ip,
        username=username,
        password=password,
    )

    if ssh is None:

        for destination in destinations:

            if destination["ip"] == source_ip:

                results[destination["node"]] = {
                    "status": "-",
                    "message": "Same VM",
                }

            else:

                results[destination["node"]] = {
                    "status": "✕",
                    "message": (
                        f"SSH failed to source VM: "
                        f"{error}"
                    ),
                }

        return results

    try:

        for destination in destinations:

            destination_name = destination["node"]
            destination_ip = destination["ip"]

            # ------------------------------------------------
            # Same VM
            # ------------------------------------------------

            if destination_ip == source_ip:

                results[destination_name] = {
                    "status": "-",
                    "message": "Same VM",
                }

                continue

            # ------------------------------------------------
            # Ping
            # ------------------------------------------------

            command = (
                f"ping -c 2 -W 2 "
                f"{destination_ip}"
            )

            try:

                stdin, stdout, stderr = (
                    ssh.exec_command(
                        command,
                        timeout=8,
                    )
                )

                exit_code = (
                    stdout.channel.recv_exit_status()
                )

                stdout_text = (
                    stdout.read()
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

                stderr_text = (
                    stderr.read()
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

                if exit_code == 0:

                    results[destination_name] = {
                        "status": "✓",
                        "message": "Reachable",
                    }

                else:

                    results[destination_name] = {
                        "status": "✕",
                        "message": (
                            stderr_text
                            or stdout_text
                            or "Ping failed"
                        ),
                    }

            except Exception as exc:

                results[destination_name] = {
                    "status": "✕",
                    "message": str(exc),
                }

    finally:

        ssh.close()

    return results


# ============================================================
# MATRIX STYLING
# ============================================================

def style_matrix(value):

    if value == "✓":

        return (
            "color: #19c37d;"
            "font-weight: 700;"
            "font-size: 18px;"
            "text-align: center;"
        )

    if value == "✕":

        return (
            "color: #ff4d4f;"
            "font-weight: 700;"
            "font-size: 18px;"
            "text-align: center;"
        )

    if value == "...":

        return (
            "color: #98a2b3;"
            "font-weight: 700;"
            "text-align: center;"
        )

    return (
        "color: #667085;"
        "font-weight: 700;"
        "text-align: center;"
    )


# ============================================================
# CREATE MATRIX DATAFRAME
# ============================================================

def build_matrix_dataframe(
    nodes,
    matrix,
):

    rows = []

    for source in nodes:

        source_name = source["node"]

        row = {
            "Source VM": source_name
        }

        for destination in nodes:

            destination_name = destination["node"]

            row[
                destination_name
            ] = matrix[
                source_name
            ][
                destination_name
            ]

        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# RENDER VM CONNECTIVITY PAGE
# ============================================================

def render_vm_connectivity():

    # ========================================================
    # PAGE CSS
    # ========================================================

    st.markdown(
        """
        <style>

        .vm-title {
            font-size: 36px;
            font-weight: 700;
            color: #18213d;
            margin-bottom: 5px;
        }

        .vm-subtitle {
            font-size: 16px;
            color: #667085;
            margin-bottom: 25px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        '<div class="vm-title">'
        '🔗 VM Connectivity'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="vm-subtitle">'
        'Test RKE1 node-to-node network connectivity '
        'from each VM to every other VM.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ========================================================
    # STEP 1
    # KUBECONFIG
    # ========================================================

    st.markdown(
        "## 📄 Step 1: Upload Kubeconfig"
    )

    uploaded_file = st.file_uploader(
        "Upload kubeconfig",
        type=[
            "yaml",
            "yml",
            "conf",
        ],
        key="vm_connectivity_kubeconfig",
    )

    if uploaded_file is None:

        st.info(
            "Upload a kubeconfig file to continue."
        )

        return

    kubeconfig_bytes = (
        uploaded_file.getvalue()
    )

    st.success(
        f"✓ Connected using "
        f"{uploaded_file.name}"
    )

    # ========================================================
    # STEP 2
    # SSH CONFIGURATION
    # ========================================================

    st.markdown(
        "## 🔐 Step 2: VM SSH Configuration"
    )

    col1, col2 = st.columns(2)

    with col1:

        username = st.text_input(
            "RKE1 Node SSH Username",
            value="ananth.rajathinam",
            key="vm_connectivity_username",
        )

    with col2:

        password = st.text_input(
            "VM SSH Password",
            type="password",
            key="vm_connectivity_password",
        )

    # ========================================================
    # DISCOVER NODES
    # ========================================================

    if st.button(
        "🔍 Discover RKE1 Nodes",
        use_container_width=True,
    ):

        with st.spinner(
            "Reading RKE1 nodes..."
        ):

            nodes, error = get_rke1_nodes(
                kubeconfig_bytes
            )

        if error:

            st.error(
                f"Failed to get RKE1 nodes: "
                f"{error}"
            )

            return

        if not nodes:

            st.warning(
                "No RKE1 nodes with InternalIP found."
            )

            return

        # Save nodes
        st.session_state[
            "vm_connectivity_nodes"
        ] = nodes

        # Reset results
        st.session_state[
            "vm_connectivity_results"
        ] = {}

        st.success(
            f"Found {len(nodes)} RKE1 nodes."
        )

    # ========================================================
    # GET NODES
    # ========================================================

    nodes = st.session_state.get(
        "vm_connectivity_nodes",
        [],
    )

    if not nodes:
        return

    # ========================================================
    # NODE LIST
    # ========================================================

    st.markdown(
        "## 🖥️ RKE1 Nodes"
    )

    node_df = pd.DataFrame(
        [
            {
                "RKE1 Node": node["node"],
                "Internal IP": node["ip"],
            }
            for node in nodes
        ]
    )

    st.dataframe(
        node_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ========================================================
    # STEP 3
    # MATRIX
    # ========================================================

    st.markdown(
        "## 📊 VM Connectivity Matrix"
    )

    st.caption(
        "The matrix is generated first. "
        "Each source VM is then tested once against "
        "all destination VMs."
    )

    # ========================================================
    # INITIAL MATRIX
    # ========================================================

    matrix = {}

    for source in nodes:

        source_name = source["node"]

        matrix[source_name] = {}

        for destination in nodes:

            destination_name = (
                destination["node"]
            )

            if (
                source_name
                == destination_name
            ):

                matrix[
                    source_name
                ][
                    destination_name
                ] = "-"

            else:

                matrix[
                    source_name
                ][
                    destination_name
                ] = "..."

    # ========================================================
    # MATRIX PLACEHOLDER
    # ========================================================

    matrix_placeholder = st.empty()

    initial_df = build_matrix_dataframe(
        nodes,
        matrix,
    )

    matrix_placeholder.dataframe(
        initial_df.style.map(
            style_matrix
        ),
        use_container_width=True,
        hide_index=True,
        height=650,
    )

    # ========================================================
    # STEP 4
    # RUN TEST
    # ========================================================

    st.markdown(
        "## 🚀 Run Connectivity Test"
    )

    if not username:

        st.warning(
            "Please enter the SSH username."
        )

        return

    if not password:

        st.warning(
            "Please enter the SSH password."
        )

        return

    if st.button(
        "🚀 Start VM Connectivity Test",
        type="primary",
        use_container_width=True,
    ):

        live_matrix = {}

        for source in nodes:

            source_name = source["node"]

            live_matrix[
                source_name
            ] = {}

            for destination in nodes:

                destination_name = (
                    destination["node"]
                )

                if (
                    source_name
                    == destination_name
                ):

                    live_matrix[
                        source_name
                    ][
                        destination_name
                    ] = "-"

                else:

                    live_matrix[
                        source_name
                    ][
                        destination_name
                    ] = "..."

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        progress = st.progress(0)

        status_box = st.empty()

        total_sources = len(nodes)

        # ----------------------------------------------------
        # ONE SSH CONNECTION PER SOURCE
        # ----------------------------------------------------

        for index, source in enumerate(nodes):

            source_name = source["node"]
            source_ip = source["ip"]

            status_box.info(
                f"🔍 Testing from "
                f"{source_name} "
                f"({source_ip})..."
            )

            # ------------------------------------------------
            # One SSH connection
            # Then ping all destination VMs
            # ------------------------------------------------

            source_results = (
                test_all_from_source(
                    source_ip=source_ip,
                    destinations=nodes,
                    username=username,
                    password=password,
                )
            )

            # ------------------------------------------------
            # Update matrix
            # ------------------------------------------------

            for destination_name, result in (
                source_results.items()
            ):

                live_matrix[
                    source_name
                ][
                    destination_name
                ] = result[
                    "status"
                ]

            # ------------------------------------------------
            # Update UI immediately
            # ------------------------------------------------

            updated_df = (
                build_matrix_dataframe(
                    nodes,
                    live_matrix,
                )
            )

            matrix_placeholder.dataframe(
                updated_df.style.map(
                    style_matrix
                ),
                use_container_width=True,
                hide_index=True,
                height=650,
            )

            progress.progress(
                (index + 1)
                / total_sources
            )

        # ----------------------------------------------------
        # Save final results
        # ----------------------------------------------------

        st.session_state[
            "vm_connectivity_results"
        ] = live_matrix

        status_box.success(
            "✅ VM-to-VM connectivity test completed."
        )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    results = st.session_state.get(
        "vm_connectivity_results",
        {},
    )

    if not results:
        return

    # ========================================================
    # SUMMARY
    # ========================================================

    success_count = 0
    failed_count = 0

    for source_name in results:

        for destination_name in results[
            source_name
        ]:

            value = results[
                source_name
            ][
                destination_name
            ]

            if value == "✓":
                success_count += 1

            elif value == "✕":
                failed_count += 1

    st.markdown(
        "## 📈 Connectivity Summary"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "✓ Successful",
            success_count,
        )

    with col2:

        st.metric(
            "✕ Failed",
            failed_count,
        )

    with col3:

        st.metric(
            "Total Connections",
            success_count + failed_count,
        )

    # ========================================================
    # FAILED CONNECTIONS
    # ========================================================

    if failed_count > 0:

        st.markdown(
            "## ❌ Failed VM Connections"
        )

        ip_map = {
            node["node"]: node["ip"]
            for node in nodes
        }

        failed_rows = []

        # We need detailed failure information.
        # Re-test the failed entries only for details.

        for source in nodes:

            source_name = source["node"]

            for destination in nodes:

                destination_name = (
                    destination["node"]
                )

                if (
                    results[
                        source_name
                    ][
                        destination_name
                    ]
                    != "✕"
                ):
                    continue

                failed_rows.append(
                    {
                        "Source VM": source_name,
                        "Source IP": ip_map.get(
                            source_name,
                            "",
                        ),
                        "Destination VM": (
                            destination_name
                        ),
                        "Destination IP": (
                            ip_map.get(
                                destination_name,
                                "",
                            )
                        ),
                        "Status": "FAILED",
                    }
                )

        st.dataframe(
            pd.DataFrame(
                failed_rows
            ),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.success(
            "🎉 All VM-to-VM connectivity tests passed."
        )