package mx.sigic.gs.wpsdownload.excel;

import org.geoserver.wps.ppio.ComplexPPIO;

import org.geotools.data.simple.SimpleFeatureCollection;
import org.geotools.feature.FeatureIterator;

import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.io.WKTWriter;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.InputStream;
import java.io.OutputStream;
import java.io.IOException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

public class XlsxPPIO extends ComplexPPIO {

    public static final String MIME_XLSX =
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    public XlsxPPIO() {
        // external type = OutputStream, internal binding = SimpleFeatureCollection
        super(OutputStream.class, SimpleFeatureCollection.class, MIME_XLSX);
    }

    @Override
    public void encode(Object value, OutputStream os) throws Exception {
        SimpleFeatureCollection fc = (SimpleFeatureCollection) value;

        try (Workbook wb = new XSSFWorkbook()) {
            Sheet sh = wb.createSheet("data");
            WKTWriter wkt = new WKTWriter();

            // header
            List<String> headers = null;
            int r = 0;

            try (FeatureIterator<?> it = fc.features()) {
                while (it.hasNext()) {
                    Object f = it.next();

                    if (headers == null) {
                        headers = extractHeadersFromFeature(f);
                        Row header = sh.createRow(r++);
                        for (int c = 0; c < headers.size(); c++) {
                            header.createCell(c).setCellValue(headers.get(c));
                        }
                    }

                    Row row = sh.createRow(r++);
                    for (int c = 0; c < headers.size(); c++) {
                        Object v = getAttributeByIndex(f, c);
                        Cell cell = row.createCell(c);
                        if (v == null) {
                            cell.setBlank();
                        } else if (v instanceof Number) {
                            cell.setCellValue(((Number) v).doubleValue());
                        } else if (v instanceof java.util.Date) {
                            cell.setCellValue((java.util.Date) v);
                        } else if (v instanceof Geometry) {
                            cell.setCellValue(wkt.write((Geometry) v));
                        } else {
                            cell.setCellValue(String.valueOf(v));
                        }
                    }
                }
            }

            if (headers != null) {
                for (int c = 0; c < Math.min(headers.size(), 50); c++) {
                    sh.autoSizeColumn(c);
                }
            }

            wb.write(os);
        } catch (RuntimeException e) {
            throw new IOException("Error generando XLSX", e);
        }
    }

    @Override
    public Object decode(InputStream input) throws Exception {
        // No soportamos decodificación (solo ENCODING)
        throw new UnsupportedOperationException("XLSX decode no soportado");
    }

    @Override
    public String getFileExtension() { return "xlsx"; }

    // ===== Helpers por reflexión para evitar gt-opengis =====

    @SuppressWarnings("unchecked")
    private static List<String> extractHeadersFromFeature(Object feature) {
        try {
            Object ft = feature.getClass().getMethod("getFeatureType").invoke(feature);
            Method getAttrDesc = ft.getClass().getMethod("getAttributeDescriptors");
            List<Object> descriptors = (List<Object>) getAttrDesc.invoke(ft);

            List<String> headers = new ArrayList<>(descriptors.size());
            for (Object d : descriptors) {
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
            throw new RuntimeException("No pude leer encabezados vía reflexión", e);
        }
    }

    private static Object getAttributeByIndex(Object feature, int index) {
        try {
            return feature.getClass().getMethod("getAttribute", int.class).invoke(feature, index);
        } catch (Exception e) {
            throw new RuntimeException("No pude leer atributo[" + index + "]", e);
        }
    }
}
