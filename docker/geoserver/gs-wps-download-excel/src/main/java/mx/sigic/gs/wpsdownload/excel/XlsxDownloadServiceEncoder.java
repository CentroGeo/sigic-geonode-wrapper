package mx.sigic.gs.wpsdownload.excel;

import org.geoserver.wps.download.DownloadServiceEncoder;

import org.geotools.data.simple.SimpleFeatureCollection;
import org.geotools.feature.FeatureIterator;

import org.opengis.util.ProgressListener;               // OGC (no GeoTools)
import org.opengis.feature.simple.SimpleFeature;        // OGC
import org.opengis.feature.simple.SimpleFeatureType;    // OGC

import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.io.WKTWriter;

import java.io.IOException;
import java.io.OutputStream;
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

        try (SXSSFWorkbook wb = new SXSSFWorkbook(100)) { // ~100 filas en memoria
            Sheet sheet = wb.createSheet("data");

            SimpleFeatureType schema = features.getSchema();
            int colCount = schema.getAttributeCount();

            // Encabezados
            Row header = sheet.createRow(0);
            for (int c = 0; c < colCount; c++) {
                header.createCell(c).setCellValue(schema.getDescriptor(c).getLocalName());
            }

            // Estilos
            CreationHelper ch = wb.getCreationHelper();
            CellStyle dateStyle = wb.createCellStyle();
            dateStyle.setDataFormat(ch.createDataFormat().getFormat("yyyy-mm-dd hh:mm:ss"));

            WKTWriter wkt = new WKTWriter();
            int r = 1;

            try (FeatureIterator<SimpleFeature> it = features.features()) {
                while (it.hasNext()) {
                    SimpleFeature f = it.next();
                    Row row = sheet.createRow(r++);
                    for (int c = 0; c < colCount; c++) {
                        Object v = f.getAttribute(c);
                        Cell cell = row.createCell(c);
                        if (v == null) {
                            cell.setBlank();
                        } else if (v instanceof Geometry) {
                            cell.setCellValue(wkt.write((Geometry) v));
                        } else if (v instanceof Number) {
                            cell.setCellValue(((Number) v).doubleValue());
                        } else if (v instanceof java.util.Date) {
                            cell.setCellValue((java.util.Date) v);
                            cell.setCellStyle(dateStyle);
                        } else {
                            cell.setCellValue(String.valueOf(v));
                        }
                    }
                }
            }

            // Auto-ajuste (limitar por performance)
            for (int c = 0; c < Math.min(colCount, 25); c++) {
                sheet.autoSizeColumn(c);
            }

            wb.write(out);
            wb.dispose(); // limpia temporales
        }
    }
}
