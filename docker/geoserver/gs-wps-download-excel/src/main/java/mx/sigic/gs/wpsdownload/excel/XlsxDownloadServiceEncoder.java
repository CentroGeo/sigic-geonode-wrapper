package mx.sigic.gs.wpsdownload.excel;

import org.geoserver.wps.download.DownloadServiceEncoder;

import org.geotools.data.simple.SimpleFeatureCollection;
import org.geotools.feature.FeatureIterator;
import org.geotools.util.ProgressListener;

import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.io.WKTWriter;

import java.io.IOException;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.poi.xssf.streaming.SXSSFWorkbook;
import org.apache.poi.ss.usermodel.*;

public class XlsxDownloadServiceEncoder implements DownloadServiceEncoder {

    public static final String MIME_XLSX =
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    @Override
    public Set<String> getOutputMimeTypes() {
        return Set.of(MIME_XLSX);
    }

    @Override
    public void encode(SimpleFeatureCollection features,
                       OutputStream out,
                       Map<String, Object> encoderParams,
                       ProgressListener listener) throws IOException {

        try (SXSSFWorkbook wb = new SXSSFWorkbook(100)) {
            Sheet sheet = wb.createSheet("data");

            // Estilos
            CreationHelper ch = wb.getCreationHelper();
            CellStyle dateStyle = wb.createCellStyle();
            dateStyle.setDataFormat(ch.createDataFormat().getFormat("yyyy-mm-dd hh:mm:ss"));

            WKTWriter wkt = new WKTWriter();

            List<String> headers = new ArrayList<>();
            boolean headerWritten = false;
            int rowIndex = 0;

            try (FeatureIterator<?> it = features.features()) {
                while (it.hasNext()) {
                    Object f = it.next();

                    // Construir encabezados desde el primer feature, vía reflexión
                    if (!headerWritten) {
                        headers = extractHeadersFromFeature(f);
                        Row header = sheet.createRow(rowIndex++);
                        for (int c = 0; c < headers.size(); c++) {
                            header.createCell(c).setCellValue(headers.get(c));
                        }
                        headerWritten = true;
                    }

                    Row row = sheet.createRow(rowIndex++);
                    for (int c = 0; c < headers.size(); c++) {
                        Object v = getAttributeByIndex(f, c);
                        Cell cell = row.createCell(c);
                        if (v == null) {
                            cell.setBlank();
                        } else if (v instanceof Number) {
                            cell.setCellValue(((Number) v).doubleValue());
                        } else if (v instanceof java.util.Date) {
                            cell.setCellValue((java.util.Date) v);
                            cell.setCellStyle(dateStyle);
                        } else if (v instanceof Geometry) {
                            cell.setCellValue(wkt.write((Geometry) v));
                        } else {
                            cell.setCellValue(String.valueOf(v));
                        }
                    }
                }
            }

            // Auto-size (limitar para no afectar performance)
            for (int c = 0; c < Math.min(headers.size(), 25); c++) {
                sheet.autoSizeColumn(c);
            }

            wb.write(out);
            wb.dispose();
        } catch (RuntimeException e) {
            // Envuelve excepciones de reflexión en IOException para la firma
            throw new IOException("Error generando XLSX", e);
        }
    }

    // ===== Helpers con reflexión (evitan dependencia de gt-opengis) =====

    @SuppressWarnings("unchecked")
    private static List<String> extractHeadersFromFeature(Object feature) {
        try {
            // SimpleFeatureType ft = feature.getFeatureType();
            Object ft = feature.getClass().getMethod("getFeatureType").invoke(feature);

            // List<AttributeDescriptor> desc = ft.getAttributeDescriptors();
            Method getAttrDesc = ft.getClass().getMethod("getAttributeDescriptors");
            List<Object> descriptors = (List<Object>) getAttrDesc.invoke(ft);

            List<String> headers = new ArrayList<>(descriptors.size());
            for (Object d : descriptors) {
                // Name name = d.getName(); String col = name.getLocalPart();
                Object name = d.getClass().getMethod("getName").invoke(d);
                String col;
                try {
                    col = (String) name.getClass().getMethod("getLocalPart").invoke(name);
                } catch (NoSuchMethodException nsme) {
                    col = String.valueOf(name);
                }
                headers.add(col);
            }
            return headers;
        } catch (Exception e) {
            throw new RuntimeException("No pude leer encabezados del Feature vía reflexión", e);
        }
    }

    private static Object getAttributeByIndex(Object feature, int index) {
        try {
            return feature.getClass().getMethod("getAttribute", int.class).invoke(feature, index);
        } catch (Exception e) {
            throw new RuntimeException("No pude leer atributo[" + index + "] del Feature", e);
        }
    }
}
