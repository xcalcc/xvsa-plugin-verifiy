package io.xc5.plugin.verifier;

public class MangleTool {
  private static String mangleClass(String clazzName) {
    StringBuilder mangleName = new StringBuilder();
    mangleName.append('N');
    String qualifiedName = clazzName;
    String[] spName = qualifiedName.split("\\.");
    for (String sp : spName) {
      mangleName.append(sp.getBytes().length);
      mangleName.append(sp);
    }
    return mangleName.toString();
  }
  public static String mangleClassSymbolName(String clazzName) {
    StringBuilder builder = new StringBuilder();
    builder.append("_Z");
    builder.append(mangleClass(clazzName));
    builder.append("6class$E");
    return builder.toString();
  }
}
