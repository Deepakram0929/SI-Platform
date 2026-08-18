import streamlit as st
import tempfile
import os
import subprocess
import pandas as pd

from kubernetes import client
from kubernetes.client import Configuration


# ============================================================
# KUBECONFIG LOADER
# ============================================================

def load_kubeconfig(uploaded_file):

    if uploaded_file is None:
        return None

    try:

        kubeconfig_content = uploaded_file.getvalue()

        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=".yaml",
        ) as tmp:

            tmp.write(kubeconfig_content)
            kubeconfig_path = tmp.name

        try:

            # Compatible with current Kubernetes Python client
            from kubernetes import config

            config.load_kube_config(
                config_file=kubeconfig_path
            )

            return client.ApiClient()

        finally:

            try:
                os.unlink(kubeconfig_path)
            except Exception:
                pass

    except Exception as exc:

        raise Exception(
            f"Unable to load kubeconfig: {exc}"
        )


# ============================================================
# GET INGRESS
# ============================================================

def get_ingresses(api_client, namespace):

    networking_api = client.NetworkingV1Api(
        api_client
    )

    if namespace == "All Namespaces":

        result = (
            networking_api
            .list_ingress_for_all_namespaces()
        )

    else:

        result = (
            networking_api
            .list_namespaced_ingress(
                namespace
            )
        )

    rows = []

    for ingress in result.items:

        ingress_namespace = (
            ingress.metadata.namespace
        )

        ingress_name = (
            ingress.metadata.name
        )

        hosts = []

        if ingress.spec and ingress.spec.rules:

            for rule in ingress.spec.rules:

                if rule.host:
                    hosts.append(rule.host)

        addresses = []

        if ingress.status and ingress.status.load_balancer:

            if ingress.status.load_balancer.ingress:

                for item in (
                    ingress
                    .status
                    .load_balancer
                    .ingress
                ):

                    if item.ip:
                        addresses.append(
                            item.ip
                        )

                    if item.hostname:
                        addresses.append(
                            item.hostname
                        )

        ports = set()

        if ingress.spec and ingress.spec.tls:

            ports.add("443")

        if not ports:

            ports.add("80")

        rows.append(
            {
                "Namespace": ingress_namespace,
                "Ingress Name": ingress_name,
                "Host": ", ".join(hosts),
                "Address / IP": ", ".join(addresses),
                "Ports": ", ".join(
                    sorted(ports)
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# CURL --RESOLVE CHECK
# ============================================================

def check_ip(hostname, ip, timeout=5):

    command = [
        "curl",
        "-k",
        "-s",
        "--connect-timeout",
        str(timeout),
        "--resolve",
        f"{hostname}:443:{ip}",
        f"https://{hostname}/",
        "-o",
        os.devnull,
        "-w",
        "%{http_code}",
    ]

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )

        http_code = result.stdout.strip()

        if (
            result.returncode == 0
            and http_code
            and http_code != "000"
        ):

            return True, http_code

        return False, http_code or "000"

    except subprocess.TimeoutExpired:

        return False, "TIMEOUT"

    except FileNotFoundError:

        return False, "CURL_NOT_FOUND"

    except Exception as exc:

        return False, str(exc)


# ============================================================
# MAIN PAGE
# ============================================================

def render_ingress():

    st.markdown(
        """
        <style>

        .page-title {
            font-size: 36px;
            font-weight: 700;
            color: #18213d;
        }

        .page-subtitle {
            font-size: 16px;
            color: #667085;
            margin-bottom: 24px;
        }

        .status-working {
            color: #087443;
            font-weight: 700;
        }

        .status-not-working {
            color: #d92d20;
            font-weight: 700;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        '<div class="page-title">🌐 Ingress</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'List Kubernetes Ingress resources and test '
        'Ingress IP connectivity.'
        '</div>',
        unsafe_allow_html=True,
    )


    # ========================================================
    # KUBECONFIG
    # ========================================================

    st.markdown("### Kubernetes Cluster")

    uploaded_file = st.file_uploader(
        "Upload kubeconfig",
        type=[
            "yaml",
            "yml",
            "conf",
        ],
        key="ingress_kubeconfig",
    )


    if uploaded_file is None:

        st.info(
            "Upload a kubeconfig file to scan Ingress resources."
        )

        return


    # ========================================================
    # CONNECT
    # ========================================================

    try:

        api_client = load_kubeconfig(
            uploaded_file
        )

        st.success(
            "Successfully connected to Kubernetes cluster."
        )

    except Exception as exc:

        st.error(
            f"Failed to connect to Kubernetes cluster: {exc}"
        )

        return


    # ========================================================
    # GET NAMESPACES
    # ========================================================

    try:

        core_api = client.CoreV1Api(
            api_client
        )

        namespaces_response = (
            core_api.list_namespace()
        )

        namespaces = [
            item.metadata.name
            for item in namespaces_response.items
        ]

        namespaces = sorted(namespaces)

    except Exception as exc:

        st.error(
            f"Failed to list namespaces: {exc}"
        )

        return


    # ========================================================
    # SEARCH OPTIONS
    # ========================================================

    st.divider()

    st.markdown(
        "### 🔎 Ingress Search"
    )

    col1, col2 = st.columns(2)


    with col1:

        selected_namespace = st.selectbox(
            "Select Namespace",
            [
                "All Namespaces"
            ] + namespaces,
            key="ingress_namespace",
        )


    with col2:

        ingress_filter = st.text_input(
            "Ingress Name / Host Filter",
            value="",
            placeholder="Example: dclm",
            key="ingress_filter",
        )


    # ========================================================
    # LOAD INGRESS
    # ========================================================

    if st.button(
        "🔍 Load Ingress",
        use_container_width=True,
        type="primary",
        key="load_ingress",
    ):

        try:

            df = get_ingresses(
                api_client,
                selected_namespace,
            )

            if df.empty:

                st.warning(
                    "No Ingress resources found."
                )

                st.session_state.ingress_df = (
                    pd.DataFrame()
                )

            else:

                # --------------------------------------------
                # FILTER
                # --------------------------------------------

                if ingress_filter.strip():

                    search_value = (
                        ingress_filter
                        .strip()
                        .lower()
                    )

                    mask = (
                        df["Ingress Name"]
                        .str.lower()
                        .str.contains(
                            search_value,
                            na=False,
                        )
                        |
                        df["Host"]
                        .str.lower()
                        .str.contains(
                            search_value,
                            na=False,
                        )
                    )

                    df = df[mask]


                st.session_state.ingress_df = df

        except Exception as exc:

            st.error(
                f"Failed to load Ingress: {exc}"
            )


    # ========================================================
    # DISPLAY INGRESS
    # ========================================================

    if (
        "ingress_df"
        not in st.session_state
    ):

        return


    df = st.session_state.ingress_df


    if df.empty:

        st.warning(
            "No matching Ingress found."
        )

        return


    st.divider()

    st.markdown(
        "### 🌐 Kubernetes Ingress"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


   # ============================================================
    # INGRESS IP CONNECTIVITY CHECK
    # ============================================================

    st.divider()

    st.markdown(
        "### 🔗 Ingress IP Connectivity Check"
    )

    st.caption(
        "IP addresses are automatically taken from the selected "
        "Kubernetes Ingress."
    )


    # ============================================================
    # SELECT INGRESS
    # ============================================================

    ingress_df = st.session_state.get(
        "ingress_df",
        pd.DataFrame()
    )


    if ingress_df.empty:

        st.info(
            "Load Ingress resources first."
        )

        return


    # Create ingress selection

    ingress_options = []

    for index, row in ingress_df.iterrows():

        ingress_options.append(
            f"{index} | "
            f"{row['Ingress Name']} | "
            f"{row['Host']}"
        )


    selected_ingress = st.selectbox(
        "Select Ingress",
        ingress_options,
        key="selected_ingress",
    )


    selected_ingress_index = int(
        selected_ingress.split("|")[0].strip()
    )


    selected_ingress_row = ingress_df.loc[
        selected_ingress_index
    ]


    # ============================================================
    # HOSTNAME
    # ============================================================

    selected_host = (
        selected_ingress_row["Host"]
    )


    # If multiple hosts exist, use the first one

    if "," in str(selected_host):

        host_list = [
            h.strip()
            for h in str(selected_host).split(",")
            if h.strip()
        ]

        hostname = st.selectbox(
            "Hostname",
            host_list,
            key="selected_ingress_hostname",
        )

    else:

        hostname = st.text_input(
            "Hostname",
            value=str(selected_host),
            disabled=True,
            key="selected_ingress_hostname",
        )


    # ============================================================
    # GET IP ADDRESSES FROM SELECTED INGRESS
    # ============================================================

    address_value = (
        selected_ingress_row["Address / IP"]
    )


    ingress_ips = []

    if address_value:

        ingress_ips = [
            ip.strip()
            for ip in str(address_value).split(",")
            if ip.strip()
        ]


    # ============================================================
    # DISPLAY INGRESS IPs
    # ============================================================

    st.markdown(
        "#### 🌐 Ingress IP Addresses"
    )


    if not ingress_ips:

        st.warning(
            "No IP address is currently available in "
            "Ingress status.loadBalancer."
        )

        st.caption(
            "Check the Ingress with: "
            "`kubectl get ingress -n <namespace> -o wide`"
        )

    else:

        st.success(
            f"{len(ingress_ips)} IP address(es) found "
            "from the selected Ingress."
        )


        ip_df = pd.DataFrame(
            {
                "Ingress IP": ingress_ips
            }
        )


        st.dataframe(
            ip_df,
            use_container_width=True,
            hide_index=True,
        )


    # ============================================================
    # CONNECTION TIMEOUT
    # ============================================================

    col1, col2 = st.columns(2)


    with col1:

        timeout = st.number_input(
            "Connection Timeout (seconds)",
            min_value=1,
            max_value=60,
            value=5,
            step=1,
            key="ingress_timeout",
        )


    with col2:

        st.markdown(
            "<br>",
            unsafe_allow_html=True,
        )

        st.caption(
            "Equivalent to:"
        )

        st.code(
            "curl -k -s --connect-timeout 5 "
            "--resolve HOST:443:IP "
            "https://HOST/",
            language="bash",
        )


    # ============================================================
    # CHECK ALL IPS
    # ============================================================

    if st.button(
        "🔎 Check All Ingress IPs",
        use_container_width=True,
        type="primary",
        key="check_ingress_ips",
    ):

        if not hostname.strip():

            st.error(
                "Selected Ingress does not have a hostname."
            )

        elif not ingress_ips:

            st.error(
                "No Ingress IP addresses were found."
            )

        else:

            results = []

            progress = st.progress(0)


            for index, ip in enumerate(ingress_ips):

                working, response = check_ip(
                    hostname.strip(),
                    ip,
                    timeout,
                )


                if working:

                    status = "WORKING"

                else:

                    status = "NOT WORKING"


                results.append(
                    {
                        "Namespace":
                            selected_ingress_row[
                                "Namespace"
                            ],

                        "Ingress Name":
                            selected_ingress_row[
                                "Ingress Name"
                            ],

                        "Hostname":
                            hostname,

                        "IP Address":
                            ip,

                        "Status":
                            status,

                        "HTTP Code":
                            response,
                    }
                )


                progress.progress(
                    (index + 1) / len(ingress_ips)
                )


            progress.empty()


            st.session_state.ingress_results = (
                pd.DataFrame(results)
            )


    # ============================================================
    # RESULTS
    # ============================================================

    if "ingress_results" in st.session_state:

        results_df = (
            st.session_state.ingress_results
        )


        st.divider()

        st.markdown(
            "### 📊 Connectivity Results"
        )


        working_count = (
            results_df["Status"]
            .eq("WORKING")
            .sum()
        )


        not_working_count = (
            results_df["Status"]
            .eq("NOT WORKING")
            .sum()
        )


        c1, c2, c3 = st.columns(3)


        with c1:

            st.metric(
                "Total IPs",
                len(results_df),
            )


        with c2:

            st.metric(
                "✅ Working",
                working_count,
            )


        with c3:

            st.metric(
                "❌ Not Working",
                not_working_count,
            )


        # ========================================================
        # COLOR STATUS
        # ========================================================

        def color_status(value):

            if value == "WORKING":

                return (
                    "background-color: #dcfce7;"
                    "color: #166534;"
                    "font-weight: 700;"
                )

            return (
                "background-color: #fee2e2;"
                "color: #991b1b;"
                "font-weight: 700;"
            )


        styled_df = (
            results_df
            .style
            .map(
                color_status,
                subset=["Status"],
            )
        )


        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
        )


        # ========================================================
        # EXCEL DOWNLOAD
        # ========================================================

        import io


        excel_buffer = io.BytesIO()


        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl",
        ) as writer:

            results_df.to_excel(
                writer,
                index=False,
                sheet_name="Ingress Check",
            )


        st.download_button(
            "⬇️ Download Excel",
            data=excel_buffer.getvalue(),
            file_name=(
                "ingress_connectivity_results.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True,
        )