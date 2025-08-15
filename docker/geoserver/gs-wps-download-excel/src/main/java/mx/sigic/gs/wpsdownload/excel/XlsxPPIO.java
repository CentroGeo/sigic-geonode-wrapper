package mx.sigic.wps.excel;

import java.io.OutputStream;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.geoserver.wps.ppio.ComplexPPIO;
import org.geotools.api.data.simple.SimpleFeatureCollection;
import org.geotools.api.data.simple.SimpleFeatureIterator;
import org.geotools.api.feature.simple.SimpleFeature;
import org.geotools.api.feature.simple.SimpleFeatureType;
import org.geotools.api.feature.type.AttributeDescriptor;
import org.locationtech.jts.geom.Geometry;

public class XlsxPPIO extends ComplexPPIO {

    public XlsxPPIO() {
        super(OutputStream.class, SimpleFeatureCollection.class,
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    }

    @Override
    public void encode(Object value, OutputStream os) throws Exception {
        SimpleFeatureCollection fc = (SimpleFeatureCollection) value;
        try (Workbook wb = new XSSFWorkbook()) {
            Sheet sh = wb.createSheet("data");
            SimpleFeatureType ft = fc.getSchema();

            // Header
            Row header = sh.createRow(0);
            for (int i = 0; i < ft.getAttributeCount(); i++) {
                AttributeDescriptor ad = ft.getDescriptor(i);
                header.createCell(i).setCellValue(ad.getLocalName());
            }

            // Rows
            int r = 1;
            try (SimpleFeatureIterator it = fc.features()) {
                while (it.hasNext()) {
                    SimpleFeature f = it.next();
                    Row row = sh.createRow(r++);
                    for (int i = 0; i < ft.getAttributeCount(); i++) {
                        Object v = f.getAttribute(i);
                        Cell c = row.createCell(i);
                        if (v == null) { c.setBlank(); continue; }
                        if (v instanceof Number) {
                            c.setCellValue(((Number) v).doubleValue());
                        } else if (v instanceof java.util.Date) {
                            c.setCellValue((java.util.Date) v);
                        } else if (v instanceof Geometry) {
                            c.setCellValue(((Geometry) v).toText()); // WKT
                        } else {
                            c.setCellValue(String.valueOf(v));
                        }
                    }
                }
            }

            // autosize (hasta 50 columnas por seguridad)
            int cols = Math.min(50, ft.getAttributeCount());
            for (int i = 0; i < cols; i++) sh.autoSizeColumn(i);

            wb.write(os);
        }
    }

    @Override
    public String getFileExtension() { return "xlsx"; }

    @Override
    public PPIODirection getDirection() { return PPIODirection.ENCODING; }
}
