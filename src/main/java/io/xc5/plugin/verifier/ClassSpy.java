package io.xc5.plugin.verifier;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Member;
import java.net.URL;
import java.net.URLDecoder;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.TreeSet;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import static java.lang.System.out;

public class ClassSpy {

  public static void main(String... args) {
    try {

      Class[] myClasses = getClassesInPackage("you.package.name.here", null);

      for (Class index : myClasses)
        out.format("Class:%n  %s%n%n", index.getCanonicalName());

    } catch (ArrayIndexOutOfBoundsException e) {

      e.printStackTrace();
    }
  }

    /**
     * Scans all classes accessible from the context
     * class loader which belong to the given package
     * and subpackages. Adapted from
     * http://snippets.dzone.com/posts/show/4831
     * and extended to support use of JAR files
     * @param packageName The base package
     * @param regexFilter an optional class name pattern.
     * @return The classes
     */
    public static Class<?>[] getClassesInPackage (String packageName, String regexFilter) {

      Pattern regex = null;

      if (regexFilter != null)
        regex = Pattern.compile(regexFilter);

      try {

        ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
        assert classLoader != null;
        String path = packageName.replace('.', '/');
        Enumeration<URL> resources = classLoader.getResources(path);
        List<String> dirs = new ArrayList<String>();

        while (resources.hasMoreElements()) {

          URL resource = resources.nextElement();
          dirs.add(resource.getFile());
        }

        TreeSet<String> classes = new TreeSet<String>();
        for (String directory : dirs) {

          classes.addAll(findClasses(directory, packageName, regex));
        }

        ArrayList classList = new ArrayList();

        for (String clazz : classes) {

          classList.add(Class.forName(clazz));
        }

        return (Class[]) classList.toArray(new Class[classes.size()]);
      } catch (Exception e) {

        e.printStackTrace();
        return null;
      }

    }

    /**
     * Recursive method used to find all classes in a given path
     * (directory or zip file url). Directories are searched recursively.
     * (zip files are Adapted from http://snippets.dzone.com/posts/show/4831
     * and extended to support use of JAR files @param path The base
     * directory or url from which to search. @param packageName The package
     * name for classes found inside the base directory @param regex an
     * optional class name pattern. e.g. .*Test*
     * @return The classes
     */
    private static TreeSet findClasses (String path, String packageName, Pattern regex) throws Exception {

      TreeSet classes = new TreeSet();

      if (path.startsWith("file:") && path.contains("!")) {

        String[] split = path.split("!");
        URL jar = new URL(split[0]);

        ZipInputStream zip = new ZipInputStream(jar.openStream());
        ZipEntry entry;

        while ((entry = zip.getNextEntry()) != null) {

          System.out.println("Here 1");

          if (entry.getName().endsWith(".class")) {

            System.out.println("Here 2");

            String className = entry.getName()
                    .replaceAll("[$].*", "")
                    .replaceAll("[.]class", "")
                    .replace('/', '.');

            if (className.startsWith(packageName) && (regex == null
                    || regex.matcher(className).matches()))

              classes.add(className);
          }

        }

      }

      File dir = new File(path);

      if (!dir.exists()) {

        return classes;
      }

      File[] files = dir.listFiles();

      for (File file : files) {

        if (file.isDirectory()) {

          assert !file.getName().contains(".");
          classes.addAll(findClasses(file.getAbsolutePath()
                  , packageName + "." + file.getName()
                  , regex));
        } else if (file.getName().endsWith(".class")) {

          String className = packageName + '.' + file
                  .getName()
                  .substring(0, file.getName().length() - 6);

          if (regex == null || regex.matcher(className).matches())
            classes.add(className);
        }

      }

      return classes;
    }
}