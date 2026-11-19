#!/usr/bin/env python3
"""Geçerli Kibana Lens saved object'leri üreten yardımcı modül.

Şema, çalışan Kibana sample data panellerinden (Kibana 8.19) birebir çıkarılmıştır.
Lens'in `state` yapısı iki parçadan oluşur ve ikisi birlikte tutarlı olmak zorundadır:

  1. `datasourceStates.formBased.layers[<layerId>].columns` -> kolon TANIMLARI
  2. `visualization`                                        -> bu kolonların ID'lerine ATIFLAR

Ayrıca `references` içinde her layer için `indexpattern-datasource-layer-<layerId>`
adıyla data view bağlantısı verilmelidir; verilmezse panel hangi veriyi
sorgulayacağını bilemez ve boş/bozuk görünür.
"""

RECORDS = "___records___"


# --------------------------------------------------------------------------
# Kolon tanımları (datasourceStates içine girer)
# --------------------------------------------------------------------------
def col_count(label="Count of records", filter_query=None, filter_language="kuery"):
    """Doküman sayısı. filter_query verilirse yalnızca o filtreye uyanlar sayılır."""
    column = {
        "label": label,
        "dataType": "number",
        "operationType": "count",
        "isBucketed": False,
        "scale": "ratio",
        "sourceField": RECORDS,
        "params": {"emptyAsNull": False},
    }
    if filter_query:
        column["filter"] = {"query": filter_query, "language": filter_language}
    if label != "Count of records":
        column["customLabel"] = True
    return column


def col_percentile(field, percentile=95, label=None):
    """Yüzdelik dilim (örn. p95 gecikme).

    Şema, Kibana 8.19'in Lens paketindeki percentile `buildColumn` fonksiyonundan
    doğrulanmıştır: `operationType: "percentile"`, `sourceField` ve
    `params: { percentile: <n> }`.
    """
    return {
        "label": label or f"{percentile}th percentile of {field}",
        "dataType": "number",
        "operationType": "percentile",
        "sourceField": field,
        "isBucketed": False,
        "scale": "ratio",
        "params": {"percentile": percentile},
        "customLabel": label is not None,
    }


def col_metric(operation, field, label=None):
    """sum, average, max, min, median, unique_count ..."""
    return {
        "label": label or f"{operation} of {field}",
        "dataType": "number",
        "operationType": operation,
        "sourceField": field,
        "isBucketed": False,
        "scale": "ratio",
        "customLabel": label is not None,
    }


def col_date_histogram(field, interval="auto"):
    return {
        "label": field,
        "dataType": "date",
        "operationType": "date_histogram",
        "sourceField": field,
        "isBucketed": True,
        "scale": "interval",
        "params": {"interval": interval, "includeEmptyRows": True, "dropPartials": False},
    }


def col_terms(field, size, order_by_column_id, data_type="string"):
    return {
        "label": f"Top {size} values of {field}",
        "dataType": data_type,
        "operationType": "terms",
        "sourceField": field,
        "isBucketed": True,
        "scale": "ordinal",
        "params": {
            "size": size,
            "orderBy": {"type": "column", "columnId": order_by_column_id},
            "orderDirection": "desc",
            "otherBucket": True,
            "missingBucket": False,
            "parentFormat": {"id": "terms"},
        },
    }


def metric_column(metric, label=None):
    """Metrik tanimini kolona cevirir.

    ('count',)                         -> dokuman sayisi
    ('count', filtre_kql)              -> filtreli dokuman sayisi
    ('percentile', alan, yuzde)        -> p50/p95/p99
    ('sum'|'average'|'max'|'min'|'median'|'unique_count', alan)
    """
    operation = metric[0]
    if operation == "count":
        return col_count(label or "Count of records",
                         filter_query=metric[1] if len(metric) > 1 else None)
    if operation == "percentile":
        return col_percentile(metric[1], metric[2] if len(metric) > 2 else 95, label)
    return col_metric(operation, metric[1], label)


# --------------------------------------------------------------------------
# Ortak sarmalayıcı
# --------------------------------------------------------------------------
def _wrap(title, visualization_type, visualization, layer_id, columns, column_order,
          data_view_id, query=""):
    return {
        "attributes": {
            "title": title,
            "visualizationType": visualization_type,
            "state": {
                "visualization": visualization,
                "query": {"query": query, "language": "kuery"},
                "filters": [],
                "datasourceStates": {
                    "formBased": {
                        "layers": {
                            layer_id: {
                                "columns": columns,
                                "columnOrder": column_order,
                                "incompleteColumns": {},
                            }
                        }
                    }
                },
            },
        },
        "references": [
            {
                "type": "index-pattern",
                "id": data_view_id,
                "name": f"indexpattern-datasource-layer-{layer_id}",
            }
        ],
    }


def _ids(panel_id):
    return f"layer-{panel_id}", f"{panel_id}-bucket", f"{panel_id}-metric", f"{panel_id}-split"


# --------------------------------------------------------------------------
# Panel üreticileri
# --------------------------------------------------------------------------
def metric_panel(panel_id, title, data_view_id, metric, query="", label=None):
    """KPI kartı (lnsMetric). metric: ('count',) veya ('sum', 'alan')."""
    layer_id, _, metric_id, _ = _ids(panel_id)
    column = metric_column(metric, label)
    visualization = {"layerId": layer_id, "layerType": "data", "metricAccessor": metric_id}
    return _wrap(title, "lnsMetric", visualization, layer_id,
                 {metric_id: column}, [metric_id], data_view_id, query)


def xy_panel(panel_id, title, data_view_id, bucket, metric=None, split=None,
             series_type="bar_stacked", query="", label=None, metrics=None, labels=None):
    """Çubuk/çizgi grafik (lnsXY).

    bucket: ('date_histogram', 'alan'[, 'interval']) veya ('terms', 'alan', boyut)
    metric: ('count',) veya ('sum'|'average'|..., 'alan')
    split:  ('terms', 'alan', boyut) -> Break down by
    """
    layer_id, bucket_id, metric_id, split_id = _ids(panel_id)
    metric_list = metrics if metrics else [metric]
    label_list = labels if labels else [label] * len(metric_list)

    columns, metric_ids = {}, []
    for position, (single_metric, single_label) in enumerate(zip(metric_list, label_list)):
        current_id = metric_id if position == 0 else f"{metric_id}-{position}"
        columns[current_id] = metric_column(single_metric, single_label)
        metric_ids.append(current_id)

    if bucket[0] == "date_histogram":
        columns[bucket_id] = col_date_histogram(bucket[1], bucket[2] if len(bucket) > 2 else "auto")
    else:
        columns[bucket_id] = col_terms(bucket[1], bucket[2], metric_ids[0])
    column_order = [bucket_id]

    layer = {
        "layerId": layer_id,
        "layerType": "data",
        "seriesType": series_type,
        "accessors": metric_ids,
        "xAccessor": bucket_id,
    }
    if split:
        columns[split_id] = col_terms(split[1], split[2], metric_ids[0])
        column_order.append(split_id)
        layer["splitAccessor"] = split_id
    column_order.extend(metric_ids)

    visualization = {
        "preferredSeriesType": series_type,
        "legend": {"isVisible": True, "position": "right"},
        "valueLabels": "hide",
        "layers": [layer],
    }
    return _wrap(title, "lnsXY", visualization, layer_id, columns, column_order,
                 data_view_id, query)


def pie_panel(panel_id, title, data_view_id, slice_by, size=10, query="",
              data_type="string", metric=("count",), label=None):
    """Pie chart (lnsPie). slice_by: dilimlere ayrilacak alan adı."""
    layer_id, bucket_id, metric_id, _ = _ids(panel_id)
    columns = {
        metric_id: metric_column(metric, label),
        bucket_id: col_terms(slice_by, size, metric_id, data_type),
    }
    visualization = {
        "shape": "pie",
        "layers": [{
            "layerId": layer_id,
            "layerType": "data",
            "primaryGroups": [bucket_id],
            "metrics": [metric_id],
            "numberDisplay": "percent",
            "categoryDisplay": "default",
            "legendDisplay": "default",
            "nestedLegend": False,
        }],
    }
    return _wrap(title, "lnsPie", visualization, layer_id, columns,
                 [bucket_id, metric_id], data_view_id, query)


def table_panel(panel_id, title, data_view_id, buckets, metrics, query=""):
    """Veri tablosu (lnsDatatable).

    buckets: [('terms', 'alan', boyut), ...]
    metrics: [('count',) | ('average', 'alan'), ...]
    """
    layer_id = f"layer-{panel_id}"
    columns, order = {}, []

    metric_ids = []
    for i, metric in enumerate(metrics):
        metric_id = f"{panel_id}-metric-{i}"
        columns[metric_id] = metric_column(metric)
        metric_ids.append(metric_id)

    for i, bucket in enumerate(buckets):
        bucket_id = f"{panel_id}-bucket-{i}"
        columns[bucket_id] = col_terms(bucket[1], bucket[2], metric_ids[0])
        order.append(bucket_id)
    order.extend(metric_ids)

    visualization = {
        "layerId": layer_id,
        "layerType": "data",
        "columns": [{"columnId": column_id} for column_id in order],
    }
    return _wrap(title, "lnsDatatable", visualization, layer_id, columns, order,
                 data_view_id, query)


# --------------------------------------------------------------------------
# Dashboard kaydi: panelsJSON girdisi + ona ait reference
# --------------------------------------------------------------------------
def dashboard_panel(panel_id, lens_id, grid, ref_name=None):
    """Dashboard'un `panelsJSON` girdisini ve eslesen reference'i birlikte uretir.

    `embeddableConfig` anahtari ASLA atlanmamalidir. Kibana 8.19'te
    `dashboard-plugin/server/api/transforms/out/get_panel_references.js` su satiri
    korumasiz calistirir:

        const config = panel.embeddableConfig;
        const events = config.enhancements?.dynamicActions?.events;

    Anahtar yoksa `config` undefined olur ve dashboard acilirken
    "TypeError: Cannot read properties of undefined (reading 'enhancements')"
    firlatilir; Kibana da panoyu hic render etmeden HTTP 500 doner. Panel ve
    reference'i tek yerden uretmek bu hatanin tekrarlamasini engeller.
    """
    name = ref_name or f"panel_{panel_id}"
    panel = {
        "type": "lens",
        "panelIndex": panel_id,
        "gridData": {**grid, "i": panel_id},
        "embeddableConfig": {"enhancements": {}},
        "panelRefName": name,
    }
    return panel, {"name": name, "type": "lens", "id": lens_id}


def validate_dashboard(panels, references):
    """panelsJSON <-> references tutarliligini dogrular; hatada AssertionError."""
    names = {reference["name"] for reference in references}
    for panel in panels:
        panel_index = panel.get("panelIndex")
        assert "embeddableConfig" in panel, \
            f"{panel_index}: embeddableConfig eksik -> dashboard acilirken HTTP 500"
        assert panel["gridData"].get("i") == panel_index, \
            f"{panel_index}: gridData.i panelIndex ile ayni olmali"
        ref_name = panel.get("panelRefName")
        assert ref_name in names, \
            f"{panel_index}: panelRefName '{ref_name}' references icinde yok"
    return True


# --------------------------------------------------------------------------
# Dogrulama: uretilen nesne Lens'in bekledigi tutarliliga sahip mi?
# --------------------------------------------------------------------------
def validate(panel):
    """Yapısal tutarlılık kontrolü; hata varsa AssertionError fırlatır."""
    attributes = panel["attributes"]
    state = attributes["state"]
    layers = state["datasourceStates"]["formBased"]["layers"]
    assert len(layers) == 1, "tek layer beklenir"
    layer_id, layer = next(iter(layers.items()))

    columns = layer["columns"]
    assert columns, "columns bos olamaz"
    assert set(layer["columnOrder"]) == set(columns), "columnOrder ile columns uyusmuyor"

    names = [reference["name"] for reference in panel["references"]]
    assert f"indexpattern-datasource-layer-{layer_id}" in names, "data view referansi eksik"

    visualization = state["visualization"]
    referenced = set()
    if attributes["visualizationType"] == "lnsMetric":
        referenced.add(visualization["metricAccessor"])
        assert visualization["layerId"] == layer_id
    elif attributes["visualizationType"] == "lnsXY":
        for vis_layer in visualization["layers"]:
            assert vis_layer["layerId"] == layer_id
            referenced.update(vis_layer["accessors"])
            referenced.add(vis_layer["xAccessor"])
            if "splitAccessor" in vis_layer:
                referenced.add(vis_layer["splitAccessor"])
    elif attributes["visualizationType"] == "lnsPie":
        for vis_layer in visualization["layers"]:
            assert vis_layer["layerId"] == layer_id
            referenced.update(vis_layer["primaryGroups"])
            referenced.update(vis_layer["metrics"])
    elif attributes["visualizationType"] == "lnsDatatable":
        assert visualization["layerId"] == layer_id
        referenced.update(column["columnId"] for column in visualization["columns"])

    missing = referenced - set(columns)
    assert not missing, f"visualization tanimsiz kolonlara atif yapiyor: {missing}"

    for column_id, column in columns.items():
        if column["operationType"] == "terms":
            order_by = column["params"]["orderBy"]
            if order_by["type"] == "column":
                assert order_by["columnId"] in columns, \
                    f"{column_id} siralama kolonu bulunamadi: {order_by['columnId']}"
    return True
